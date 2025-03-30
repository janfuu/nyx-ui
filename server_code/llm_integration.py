import anvil.server
import httpx
from . import memory_state
from .prompt_builder import build_prompt


OPENAI_API_BASE = "http://localhost:5000/v1"
OPENAI_MODEL = "your-model-name"  # e.g. "gpt-4", "gemma-7b", etc.
MAX_MESSAGES = 20  # Adjustable window size, depending on token budget

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

    # Add user input
    memory_state.conversation_memory.append({"role": "user", "content": user_message})

    # Select recent context (we can make this token-aware later)
    context = memory_state.conversation_memory[-60:]  # or however many you'd like

    # Build the prompt using your Jinja2 template
    prompt = build_prompt(context)

    # 🔍 Debug print to inspect actual rendered prompt
    print("----- Rendered Prompt Start -----")
    print(prompt)
    print("------ Rendered Prompt End ------")
    print("----- Conversation Memory -----")
    for msg in memory_state.conversation_memory:
        print(f"{msg['role'].upper()}: {msg['content']}")

    payload = {
        "model": OPENAI_MODEL,
        "prompt": prompt,
        "max_tokens": 512,
        "temperature": 0.8,
        "stop": ["<end_of_turn>"]
    }

    try:
        response = httpx.post(
            f"{OPENAI_API_BASE}/completions",
            json=payload,
            timeout=60
        )
        response.raise_for_status()
        reply = response.json()["choices"][0]["text"].strip()

        # Add assistant reply to memory
        memory_state.conversation_memory.append({"role": "assistant", "content": reply})



        return {"reply": reply}
    



    except Exception as e:
        return {"reply": f"[ERROR] LLM request failed: {e}"}

