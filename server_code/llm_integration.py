import anvil.server
import httpx  # recommended over requests for async, but requests also works

OPENAI_API_BASE = "http://localhost:5000/v1"
OPENAI_MODEL = "gpt-3.5-turbo"  # e.g. "gpt-3.5-turbo" or "nyx-12b"

@anvil.server.callable
def chat_with_model(user_message, context=[]):
    headers = {"Content-Type": "application/json"}
    payload = {
        "model": OPENAI_MODEL,
        "messages": context + [{"role": "user", "content": user_message}],
        "temperature": 0.8,
    }

    try:
        response = httpx.post(f"{OPENAI_API_BASE}/chat/completions", json=payload, timeout=30)
        response.raise_for_status()
        reply = response.json()["choices"][0]["message"]["content"]
        return {"reply": reply}
    except Exception as e:
        return {"reply": f"[ERROR] LLM request failed: {e}"}
