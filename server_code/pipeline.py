import time
import datetime
import httpx
import re

from . import memory_state
from . import llm_integration
from .prompt_builder import build_prompt

response_cache = {}

### STEP 1: Validate input

def validate_input(state):
    message = state.get("user_message", "").strip()
    if not message:
        raise ValueError("Empty message")
    state["user_message"] = message


### STEP 2: Get relevant memories and current mood

def get_relevant_memories_and_mood(state):
    user_message = state["user_message"]
    state["relevant_memories"] = memory_state.get_relevant_memories(user_message)
    
    all_moods = memory_state.get_memory(memory_state.MEMORY_TYPES["EMOTIONAL"])
    mood_memories = [m for m in all_moods if 'mood' in m['key'].lower()]
    if mood_memories:
        sorted_moods = sorted(mood_memories, key=lambda m: m['key'], reverse=True)
        state["current_mood"] = sorted_moods[0]['value']
    else:
        state["current_mood"] = "neutral and curious"


### STEP 3: Inject system prompt

def build_system_prompt(state):
    if not memory_state.conversation_memory or memory_state.conversation_memory[0]['role'] != 'system':
        system_msg = llm_integration.DEFAULT_SYSTEM_MESSAGE["content"]
        state["system_message"] = {
            "role": "system",
            "content": system_msg
        }
        memory_state.conversation_memory.insert(0, state["system_message"])
    else:
        state["system_message"] = memory_state.conversation_memory[0]

    # Attach dynamic mood and memory context
    mood = state["current_mood"]
    mood_text = f"\nCURRENT MOOD: You are currently feeling {mood}.\n"

    memory_text = ""
    if state["relevant_memories"]:
        memory_text = "\nRELEVANT MEMORIES:\n" + "".join(
            f"- {m['type'].upper()}: {m['value']}\n" for m in state["relevant_memories"]
        )

    updated = state["system_message"]["content"]
    if "CURRENT MOOD:" in updated:
        updated = re.sub(r"CURRENT MOOD:.*?(\n|$)", mood_text, updated)
    else:
        updated += mood_text

    if "RELEVANT MEMORIES:" in updated:
        updated = re.sub(r"RELEVANT MEMORIES:.*?(\n|$)+", memory_text, updated)
    else:
        updated += memory_text

    state["system_message"]["content"] = updated


### STEP 4: Build full prompt

def assemble_context_and_prompt(state):
    memory_state.conversation_memory.append({"role": "user", "content": state["user_message"]})
    context = memory_state.conversation_memory[-llm_integration.MAX_MESSAGES:]
    state["context"] = context
    state["prompt"] = build_prompt(context)


### STEP 5: Call the LLM

def send_prompt_to_llm(state):
    payload = {
        "model": llm_integration.OPENAI_MODEL,
        "prompt": state["prompt"],
        "max_tokens": 1024,
        "temperature": 0.7,
        "stop": ["<end_of_turn>"]
    }
    
    start = time.time()
    response = httpx.post(
        f"{llm_integration.OPENAI_API_BASE}/completions",
        json=payload,
        timeout=llm_integration.TIMEOUT
    )
    response.raise_for_status()
    raw = response.json()["choices"][0]["text"].strip()
    end = time.time()

    state["llm_raw_reply"] = raw
    state["timing"] = {"started_at": start, "completed_at": end, "duration": end - start}


### STEP 6: Parse response

def parse_response_text(text):
    result = {"main_text": text, "thoughts": [], "images": [], "mood": None}
    result["thoughts"] = re.findall(r"<thought>(.*?)</thought>", text, re.DOTALL)
    result["images"] = re.findall(r"<image>(.*?)</image>", text, re.DOTALL)
    mood_match = re.search(r"<mood>(.*?)</mood>", text, re.DOTALL)
    if mood_match:
        result["mood"] = mood_match.group(1).strip()

    # Remove all tags from main text
    text = re.sub(r"<thought>.*?</thought>", '', text, flags=re.DOTALL)
    text = re.sub(r"<image>(.*?)</image>", '[Image: \1]', text, flags=re.DOTALL)
    text = re.sub(r"<mood>.*?</mood>", '', text, flags=re.DOTALL)
    result["main_text"] = re.sub(r'\n{3,}', '\n\n', text).strip()
    return result


def parse_llm_response(state):
    parsed = parse_response_text(state["llm_raw_reply"])
    state["parsed"] = parsed


### STEP 7: Store thoughts, update mood, cache result

def update_memory_and_cache(state):
    parsed = state["parsed"]
    user_msg = state["user_message"]

    for i, thought in enumerate(parsed["thoughts"]):
        key = f"thought_{datetime.datetime.now().isoformat()}_{i}"
        memory_state.save_memory(
            memory_type=memory_state.MEMORY_TYPES["INTERACTION"],
            key=key,
            value=f"Thought: {thought}",
            importance=7,
            source="thought_extraction"
        )

    if parsed["mood"]:
        key = f"mood_{datetime.datetime.now().isoformat()}"
        memory_state.save_memory(
            memory_type=memory_state.MEMORY_TYPES["EMOTIONAL"],
            key=key,
            value=parsed["mood"],
            importance=6,
            source="mood_extraction"
        )

    memory_state.conversation_memory.append({"role": "assistant", "content": parsed["main_text"]})
    memory_state.extract_and_save_memories(user_msg, parsed["main_text"])

    resp_id = f"resp_{int(time.time())}_{hash(user_msg) % 10000}"
    response_cache[resp_id] = {
        "raw_reply": state["llm_raw_reply"],
        "parsed": parsed,
        "timestamp": time.time()
    }

    state["final_response"] = {
        "status": "success",
        "response_id": resp_id,
        "reply": parsed["main_text"],
        "thoughts": parsed["thoughts"],
        "images": parsed["images"],
        "mood": parsed["mood"] or state["current_mood"],
        "timing": state["timing"]
    }


### Entrypoint callable
import anvil.server

@anvil.server.callable
def chat_pipeline(user_message):
    state = {"user_message": user_message}
    try:
        validate_input(state)
        get_relevant_memories_and_mood(state)
        build_system_prompt(state)
        assemble_context_and_prompt(state)
        send_prompt_to_llm(state)
        parse_llm_response(state)
        update_memory_and_cache(state)
        return state["final_response"]
    except Exception as e:
        return {"status": "error", "error": str(e)}
