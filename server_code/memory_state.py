# memory_state.py
import json
import datetime
import anvil.server

# For local testing, we'll default to using Anvil tables if available
global USE_LOCAL_STORAGE
USE_LOCAL_STORAGE = False

try:
    from anvil.tables import app_tables
    HAS_TABLES = True
    print("Anvil tables detected - using them for memory storage")
except ImportError:
    HAS_TABLES = False
    USE_LOCAL_STORAGE = True
    print("WARNING: Anvil tables not available, using local storage for memories")

# We'll use both in-memory and persistent storage
conversation_memory = []

# Local memory storage for testing without Anvil tables
local_memory_storage = []

# Define memory types
MEMORY_TYPES = {
    "FACTUAL": "factual",  # Facts about the user
    "EMOTIONAL": "emotional",  # Emotional responses/states
    "PREFERENCE": "preference",  # User preferences
    "INTERACTION": "interaction",  # Patterns in interactions
}

@anvil.server.callable
def save_memory(memory_type, key, value, importance=5, source="conversation"):
    """Save a piece of information to persistent memory"""
    global USE_LOCAL_STORAGE  # Ensure global variable is accessible
    try:
        # Print what we're saving for debugging
        print(f"SAVING MEMORY: {memory_type} - {key}: {value}")
        
        if USE_LOCAL_STORAGE:
            # Use local in-memory storage (fallback)
            now = datetime.datetime.now()
            
            # Check for existing memory
            existing = None
            for i, memory in enumerate(local_memory_storage):
                if memory.get("memory_type") == memory_type and memory.get("key") == key:
                    existing = memory
                    existing_index = i
                    break
                    
            if existing:
                # Update existing
                existing["value"] = value
                existing["updated_at"] = now
                local_memory_storage[existing_index] = existing
            else:
                # Create new
                local_memory_storage.append({
                    "memory_type": memory_type,
                    "key": key,
                    "value": value,
                    "created_at": now,
                    "updated_at": now,
                    "importance": importance,
                    "source": source,
                    "is_expired": False
                })
        else:
            # Use Anvil tables
            try:
                # Try to find existing memory
                existing = app_tables.memories.get(memory_type=memory_type, key=key)
                
                if existing:
                    # Update existing memory
                    existing["value"] = value
                    existing["updated_at"] = datetime.datetime.now()
                    print(f"Updated existing memory: {memory_type} - {key}")
                else:
                    # Create new memory
                    app_tables.memories.add_row(
                        memory_type=memory_type,
                        key=key,
                        value=value,
                        created_at=datetime.datetime.now(),
                        updated_at=datetime.datetime.now(),
                        importance=importance,
                        source=source,
                        is_expired=False
                    )
                    print(f"Created new memory: {memory_type} - {key}")
            except Exception as table_error:
                print(f"Error with Anvil tables, details: {table_error}")
                # If there's a table error, verify if the memories table exists
                try:
                    # Check if 'memories' table exists by listing its columns
                    app_tables.memories.list_columns()
                    print("'memories' table exists but encountered error")
                except:
                    print("'memories' table does not exist - needs to be created")
                    # Switch to local storage as fallback
                    USE_LOCAL_STORAGE = True
                    # Try again with local storage
                    return save_memory(memory_type, key, value, importance, source)
                
        return True
    except Exception as e:
        print(f"Error saving memory: {e}")
        # Fall back to local storage if an unexpected error occurs
        if not USE_LOCAL_STORAGE:
            USE_LOCAL_STORAGE = True
            print("Switching to local storage due to error")
            return save_memory(memory_type, key, value, importance, source)
        return False

@anvil.server.callable
def get_memory(memory_type=None, key=None):
    """Retrieve memories, optionally filtered by type and/or key"""
    try:
        if USE_LOCAL_STORAGE or not HAS_TABLES:
            # Use local in-memory storage
            if memory_type and key:
                for memory in local_memory_storage:
                    if memory.get("memory_type") == memory_type and memory.get("key") == key:
                        return {"type": memory["memory_type"], "key": memory["key"], "value": memory["value"]}
                return None
            elif memory_type:
                return [{"type": m["memory_type"], "key": m["key"], "value": m["value"]} 
                        for m in local_memory_storage if m.get("memory_type") == memory_type]
            else:
                # Return all memories
                return [{"type": m["memory_type"], "key": m["key"], "value": m["value"]} 
                        for m in local_memory_storage]
        else:
            # Use Anvil tables
            if memory_type and key:
                memory = app_tables.memories.get(memory_type=memory_type, key=key)
                return memory and {"type": memory["memory_type"], "key": memory["key"], "value": memory["value"]}
            elif memory_type:
                memories = app_tables.memories.search(memory_type=memory_type)
                return [{"type": m["memory_type"], "key": m["key"], "value": m["value"]} for m in memories]
            else:
                # Return all memories
                memories = app_tables.memories.search()
                return [{"type": m["memory_type"], "key": m["key"], "value": m["value"]} for m in memories]
    except Exception as e:
        print(f"Error retrieving memory: {e}")
        return []

def extract_and_save_memories(user_message, assistant_response):
    """Extract and save potential memories from the conversation"""
    print("EXTRACTING MEMORIES from message:", user_message)
    
    # This is a simple implementation - you can make this more sophisticated
    # with NLP or by having the LLM explicitly identify memories
    
    # Example: Extract user preferences
    preference_keywords = ["like", "love", "hate", "prefer", "favorite", "enjoy"]
    for keyword in preference_keywords:
        if keyword in user_message.lower():
            # Very simple extraction - you'll want something more robust
            memory_key = f"preference_{keyword}"
            memory_value = f"User mentioned they {keyword}: {user_message}"
            save_memory(MEMORY_TYPES["PREFERENCE"], memory_key, memory_value)
            print(f"SAVED PREFERENCE: {memory_key} = {memory_value}")
    
    # Extract emotional states
    emotion_keywords = ["happy", "sad", "angry", "excited", "worried", "anxious", "longing"]
    for keyword in emotion_keywords:
        if keyword in user_message.lower():
            memory_key = f"emotion_{keyword}"
            memory_value = f"User expressed feeling {keyword}: {user_message}"
            save_memory(MEMORY_TYPES["EMOTIONAL"], memory_key, memory_value)
            print(f"SAVED EMOTION: {memory_key} = {memory_value}")
    
    # Extract potential factual information
    # This is very basic - ideally you would use NER or other techniques
    if any(pronoun in user_message.lower() for pronoun in ["i am", "i'm", "my"]):
        memory_key = f"factual_{datetime.datetime.now().isoformat()}"
        memory_value = f"User shared personal info: {user_message}"
        save_memory(MEMORY_TYPES["FACTUAL"], memory_key, memory_value)
        print(f"SAVED FACTUAL: {memory_key} = {memory_value}")
                      
    # Just to ensure we're capturing something for testing
    save_memory(MEMORY_TYPES["INTERACTION"], f"interaction_{datetime.datetime.now().isoformat()}", 
                f"User said: {user_message[:50]}...")

def get_relevant_memories(user_message, limit=5):
    """Retrieve memories relevant to the current conversation"""
    print("GETTING RELEVANT MEMORIES for message:", user_message)
    
    # This is a simple keyword-based relevance system
    # A more advanced system might use embeddings and semantic search
    
    all_memories = get_memory()
    print(f"TOTAL MEMORIES AVAILABLE: {len(all_memories)}")
    
    if not all_memories:
        print("NO MEMORIES FOUND")
        # Initialize with a test memory to verify the system is working
        save_memory(MEMORY_TYPES["FACTUAL"], "test_memory", "This is a test memory to verify the system is working")
        all_memories = get_memory()
        if not all_memories:
            return []
    
    # If this is one of the first few messages, return some memories anyway
    # This helps with testing
    if len(conversation_memory) < 5:
        print("RETURNING INITIAL MEMORIES FOR TESTING")
        return all_memories[:limit]
    
    # Simple relevance scoring based on word overlap
    user_words = set(user_message.lower().split())
    scored_memories = []
    
    for memory in all_memories:
        memory_text = f"{memory['key']} {memory['value']}".lower()
        memory_words = set(memory_text.split())
        
        # Calculate simple overlap score
        overlap = len(user_words.intersection(memory_words))
        if overlap > 0:
            scored_memories.append((overlap, memory))
    
    # If no matches, return most recent memories
    if not scored_memories:
        print("NO RELEVANT MEMORIES FOUND - RETURNING RECENT ONES")
        return all_memories[:limit]
        
    # Sort by relevance score and take top results
    scored_memories.sort(reverse=True)
    memories = [memory for _, memory in scored_memories[:limit]]
    
    print(f"RELEVANT MEMORIES FOUND: {len(memories)}")
    for memory in memories:
        print(f"  - {memory['type']}: {memory['value']}")
        
    return memories