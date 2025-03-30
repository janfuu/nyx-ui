# llm_integration.py
import anvil.server
import httpx
import json
import time
from . import memory_state
from .prompt_builder import build_prompt


OPENAI_API_BASE = "http://localhost:5000/v1"
OPENAI_MODEL = "your-model-name"  # e.g. "gpt-4", "gemma-7b", etc.
MAX_MESSAGES = 20  # Adjustable window size, depending on token budget
TIMEOUT = 60  # Increase timeout for slower models
USE_STREAMING = False  # Set to True to use streaming mode

DEFAULT_SYSTEM_MESSAGE = {
    "role": "system",
    "content": (
        "You are Nyx, a curious, emotionally nuanced AI companion. "
        "You remember past conversations, have moods, and sometimes secrets. "
        "Speak naturally and stay in character. Avoid disclaimers."
    )
}


@anvil.server.callable
def chat_with_model(user_message):
    if not user_message.strip():
        return {"reply": "[ERROR] Empty message."}

    # Add default system message if it's the first exchange
    if not memory_state.conversation_memory:
        memory_state.conversation_memory.append({
            "role": "system",
            "content": (
                "You are Nyx, an emotionally rich, mysterious AI companion. "
                "You remember previous interactions and express dynamic moods."
            )
        })

    # Retrieve relevant memories
    relevant_memories = memory_state.get_relevant_memories(user_message)
    
    # Create an enhanced system message with memories if they exist
    if relevant_memories:
        memory_text = "\n\nRELEVANT MEMORIES:\n"
        for memory in relevant_memories:
            memory_text += f"- {memory['type'].upper()}: {memory['value']}\n"
        
        # Update the system message with memories
        if memory_state.conversation_memory[0]['role'] == 'system':
            # Append to existing system message
            memory_state.conversation_memory[0]['content'] += memory_text
        else:
            # Insert new system message with memories
            memory_state.conversation_memory.insert(0, {
                "role": "system",
                "content": DEFAULT_SYSTEM_MESSAGE["content"] + memory_text
            })

    # Add user input
    memory_state.conversation_memory.append({"role": "user", "content": user_message})

    # Select recent context (we can make this token-aware later)
    context = memory_state.conversation_memory[-MAX_MESSAGES:]  # Limited window size

    # Build the prompt using your Jinja2 template
    prompt = build_prompt(context)

    # 🔍 Debug print to inspect actual rendered prompt
    print("----- Rendered Prompt Start -----")
    print(prompt)
    print("------ Rendered Prompt End ------")
    print("----- Conversation Memory -----")
    for msg in memory_state.conversation_memory:
        print(f"{msg['role'].upper()}: {msg['content']}")
    
    # Print memories that were included
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
            # Streaming implementation
            reply = ""
            response = httpx.post(
                f"{OPENAI_API_BASE}/completions",
                json={key: value for key, value in payload.items() if key != "stream"},  # Exclude "stream"
                timeout=TIMEOUT,
                # stream=True
            )
            response.raise_for_status()
            
            for line in response.iter_lines():
                if not line.strip():
                    continue
                    
                # Handle the stream format (varies by API)
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
            # Non-streaming implementation
            response = httpx.post(
                f"{OPENAI_API_BASE}/completions",
                json=payload,
                timeout=TIMEOUT
            )
            response.raise_for_status()
            reply = response.json()["choices"][0]["text"].strip()
            
        end_time = time.time()
        print(f"LLM request completed in {end_time - start_time:.2f} seconds")

        # Add assistant reply to memory
        memory_state.conversation_memory.append({"role": "assistant", "content": reply})

        # Extract and save memories from this interaction
        memory_state.extract_and_save_memories(user_message, reply)

        return {"reply": reply}
    
    except Exception as e:
        return {"reply": f"[ERROR] LLM request failed: {e}"}


@anvil.server.callable
def get_conversation_history(limit=10):
    """Return recent conversation history for display in UI"""
    if len(memory_state.conversation_memory) <= 2:  # Just system message and maybe one exchange
        return []
    
    # Skip system message, return only actual exchanges
    history = []
    for msg in memory_state.conversation_memory[1:]:
        if msg['role'] in ['user', 'assistant']:
            history.append({
                'role': msg['role'],
                'content': msg['content']
            })
    
    return history[-limit:]  # Return most recent exchanges


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