# advanced_memory.py
import anvil.server
import json
import datetime
from anvil.tables import app_tables
import httpx
from . import memory_state
from . import llm_integration

# Constants for memory management
MEMORY_DECAY_DAYS = 30  # Memories older than this are less important
MAX_MEMORIES_PER_TYPE = 50  # Maximum memories to keep per type

@anvil.server.callable
def extract_memories_using_llm(user_message, assistant_response):
    """Use the LLM itself to identify and extract memories from conversations"""
    
    memory_extraction_prompt = f"""
    You are an AI designed to extract important information to remember about a user from conversations.
    
    USER MESSAGE: {user_message}
    
    ASSISTANT RESPONSE: {assistant_response}
    
    Please identify any important information to remember about the user from this exchange.
    Format your response as a JSON object with the following schema:
    
    {{
        "memories": [
            {{
                "type": "factual|emotional|preference|interaction",
                "key": "<memory_category>", 
                "value": "<specific_information>",
                "importance": <1-10 score>
            }}
        ]
    }}
    
    Only extract information that would be important to remember for future conversations.
    If no memories should be extracted, return an empty array.
    """
    
    payload = {
        "model": llm_integration.OPENAI_MODEL,
        "prompt": memory_extraction_prompt,
        "max_tokens": 512,
        "temperature": 0.2,
        "response_format": {"type": "json_object"}
    }
    
    try:
        response = httpx.post(
            f"{llm_integration.OPENAI_API_BASE}/completions",
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        extracted = response.json()["choices"][0]["text"].strip()
        
        # Parse the JSON response
        memory_data = json.loads(extracted)
        
        # Save extracted memories
        for memory in memory_data.get("memories", []):
            memory_state.save_memory(
                memory_type=memory["type"],
                key=memory["key"],
                value=memory["value"],
                importance=memory.get("importance", 5)
            )
            
        return {"status": "success", "memories_extracted": len(memory_data.get("memories", []))}
        
    except Exception as e:
        print(f"Memory extraction failed: {e}")
        return {"status": "failed", "error": str(e)}


@anvil.server.callable
def get_memories_by_recency(days=7, limit=10):
    """Get most recent memories, useful for refreshing context"""
    cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days)
    
    recent_memories = app_tables.memories.search(
        tables.order_by("updated_at", ascending=False),
        updated_at=q.greater_than_or_equal_to(cutoff_date)
    )
    
    return [
        {
            "type": m["memory_type"],
            "key": m["key"],
            "value": m["value"],
            "updated": m["updated_at"]
        } 
        for m in recent_memories
    ][:limit]


@anvil.server.callable
def get_memories_by_importance(min_importance=7, limit=10):
    """Get highest importance memories"""
    important_memories = app_tables.memories.search(
        tables.order_by("importance", ascending=False),
        importance=q.greater_than_or_equal_to(min_importance)
    )
    
    return [
        {
            "type": m["memory_type"],
            "key": m["key"],
            "value": m["value"],
            "importance": m["importance"]
        } 
        for m in important_memories
    ][:limit]


@anvil.server.callable
def prune_old_memories():
    """Remove or decay old, less important memories"""
    cutoff_date = datetime.datetime.now() - datetime.timedelta(days=MEMORY_DECAY_DAYS)
    
    # Find old memories
    old_memories = app_tables.memories.search(
        updated_at=q.less_than(cutoff_date),
        is_expired=q.not_equal_to(True)  # Don't process already expired memories
    )
    
    for memory in old_memories:
        # If unimportant, mark as expired
        if memory["importance"] and memory["importance"] < 4:
            memory["is_expired"] = True
        # Otherwise decay importance
        elif memory["importance"]:
            memory["importance"] = max(1, memory["importance"] - 1)
    
    return {"status": "Memory pruning complete", "processed": len(old_memories)}


@anvil.server.callable
def get_semantic_memories(query, limit=5):
    """
    Advanced function (placeholder) for semantic memory search.
    In a real implementation, this would use embeddings and vector search.
    
    This is a simplified version that uses keyword matching.
    """
    # In a real implementation, you would:
    # 1. Generate embedding for the query
    # 2. Compare with stored embeddings
    # 3. Return closest matches
    
    # Simplified implementation with keywords
    query_words = set(query.lower().split())
    all_memories = app_tables.memories.search()
    
    scored_memories = []
    for memory in all_memories:
        if memory["is_expired"]:
            continue
            
        memory_text = f"{memory['key']} {memory['value']}".lower()
        memory_words = set(memory_text.split())
        
        # Calculate word overlap
        overlap = len(query_words.intersection(memory_words))
        
        # Add importance weighting
        importance = memory.get("importance", 5)
        score = overlap * (importance / 5)
        
        if score > 0:
            scored_memories.append((score, memory))
    
    # Sort by score
    scored_memories.sort(reverse=True)
    
    # Return top memories
    return [
        {
            "type": m["memory_type"],
            "key": m["key"],
            "value": m["value"],
            "score": score
        } 
        for score, m in scored_memories
    ][:limit]