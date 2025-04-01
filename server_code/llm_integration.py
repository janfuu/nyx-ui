# llm_integration.py

import anvil.server
import httpx
import json
import time
from . import memory_state
from .prompt_builder import build_prompt

# --- Configuration ---
OPENAI_API_BASE = "http://localhost:5000/v1"
OPENAI_MODEL = "your-model-name"  # e.g. "gpt-4", "mistral", "gemma", etc.
MAX_MESSAGES = 20
TIMEOUT = 60
USE_STREAMING = False

# --- System Identity ---

DEFAULT_PERSONA = (
    "You are Nyx, a curious, emotionally nuanced AI companion. "
    "You remember past conversations, have moods, and sometimes secrets. "
    "Speak naturally and stay in character. Avoid disclaimers."
)

NYX_APPEARANCE = (
    "You have a distinctive appearance: a futuristic woman with shimmering silver skin, "
    "chrome facial accents, dark hair. "
    "You may be visualized in images when referenced as 'me', 'myself', or similar."
)

# --- System Message Builder ---

def build_system_message(mood=None, relevant_memories=None):
    parts = [DEFAULT_PERSONA, NYX_APPEARANCE]

    if mood:
        parts.append(f"\nCURRENT MOOD: You are currently feeling {mood}.")

    if relevant_memories:
        memory_lines = ["\nRELEVANT MEMORIES:"]
        for memory in relevant_memories:
            memory_lines.append(f"- {memory['type'].upper()}: {memory['value']}")
        parts.append("\n".join(memory_lines))

    return {
        "role": "system",
        "content": "\n\n".join(parts)
    }

# --- Core Chat Function ---

@anvil.server.callable
def chat_with_model(user_message):
    if not user_message.strip():
        return {"reply": "[ERROR] Empty message."}

    # Retrieve relevant memories
    relevant_memories = memory_state.get_relevant_memories(user_message)

    # Insert system message if not present
    if not memory_state.conversation_memory or memory_state.conversation_memory[0]['role'] != 'system':
        system_msg = build_system_message(relevant_memories=relevant_memories)
        memory_state.conversation_memory.insert(0, system_msg)

    # Add user input
    memory_state.conversation_memory.append({"role": "user", "content": user_message})

    # Select context window
    context = memory_state.conversation_memory[-MAX_MESSAGES:]

    # Build the full prompt using your Jinja2 template
    prompt = build_prompt(context)

    print("----- Rendered Prompt Start -----")
    print(prompt)
    print("------ Rendered Prompt End ------")
    print("----- Conversation Memory -----")
    for msg in memory_state.conversation_memory:
        print(f"{msg['role'].upper()}: {msg['content']}")

    print("----- Included Memories -----")
    if relevant_memories:
        for memory in relevant_memories:
            print(f"{memory['type']}: {memory['value']}")
    else:
        print("No memories included")

    payload = {
        "model": OPENAI_MODEL,
        "prompt": prompt,
        "max_tokens": 512,
        "temperature": 0.8,
        "stop": ["<end_of_turn>"]
    }

    try:
        start_time = time.time()
        print(f"Starting LLM request at {start_time}")

        if USE_STREAMING:
            reply = ""
            response = httpx.post(
                f"{OPENAI_API_BASE}/completions",
                json={key: value for key, value in payload.items() if key != "stream"},
                timeout=TIMEOUT,
            )
            response.raise_for_status()

            for line in response.iter_lines():
                if not line.strip():
                    continue
                try:
                    if line.startswith(b"data: "):
                        json_str = line[6:].decode("utf-8")
                        if json_str == "[DONE]":
                            break
                        chunk = json.loads(json_str)
                        if chunk["choices"][0].get("text"):
                            reply += chunk["choices"][0]["text"]
                except Exception as e:
                    print(f"Error parsing stream chunk: {e}")
        else:
            response = httpx.post(
                f"{OPENAI_API_BASE}/completions",
                json=payload,
                timeout=TIMEOUT
            )
            response.raise_for_status()
            reply = response.json()["choices"][0]["text"].strip()

        end_time = time.time()
        print(f"LLM request completed in {end_time - start_time:.2f} seconds")

        memory_state.conversation_memory.append({"role": "assistant", "content": reply})
        memory_state.extract_and_save_memories(user_message, reply)

        return {"reply": reply}

    except Exception as e:
        return {"reply": f"[ERROR] LLM request failed: {e}"}

# --- Utility APIs ---

@anvil.server.callable
def get_conversation_history(limit=10):
    """Return recent conversation history for display in UI"""
    if len(memory_state.conversation_memory) <= 2:
        return []

    history = []
    for msg in memory_state.conversation_memory[1:]:
        if msg['role'] in ['user', 'assistant']:
            history.append({'role': msg['role'], 'content': msg['content']})

    return history[-limit:]

@anvil.server.callable
def clear_conversation():
    """Reset the conversation"""
    system_message = None
    if memory_state.conversation_memory and memory_state.conversation_memory[0]['role'] == 'system':
        system_message = memory_state.conversation_memory[0]

    memory_state.conversation_memory.clear()

    if system_message:
        memory_state.conversation_memory.append(system_message)

    return {"status": "Conversation cleared"}
