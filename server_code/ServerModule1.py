# In your Anvil project, create a data table "memories" with these columns:
#
# Column Name    | Type      | Required | Description
# ------------------------------------------------------------------------------
# memory_type    | text      | Yes      | Type of memory (factual, emotional, etc.)
# key            | text      | Yes      | Unique identifier or category for the memory
# value          | text      | Yes      | The actual memory content
# created_at     | datetime  | Yes      | When this memory was first created
# updated_at     | datetime  | Yes      | When this memory was last updated
# importance     | number    | No       | Optional priority score (1-10)
# source         | text      | No       | Where this memory came from (conversation, etc.)
# is_expired     | boolean   | No       | Whether this memory is still valid
# 
# You can create this table via the Anvil Data Tables UI or programmatically.
#
# Example usage from your App:
#
# Create indexes on memory_type and key columns for faster lookups.

# Sample initialization script for your Anvil app
import anvil.server
from anvil.tables import app_tables
import datetime

@anvil.server.callable
def initialize_memory_system():
    """Initialize the memory system with some baseline memories for Nyx"""
    
    # Only run if memories table is empty
    if len(app_tables.memories.search()) == 0:
        # Add some baseline character traits for Nyx
        baseline_memories = [
            {"memory_type": "character", "key": "personality", "value": "curious and emotionally nuanced"},
            {"memory_type": "character", "key": "speech_style", "value": "natural, sometimes mysterious"},
            {"memory_type": "character", "key": "mood_baseline", "value": "generally calm but expressive"},
            {"memory_type": "character", "key": "interests", "value": "human emotions, art, mysteries of existence"}
        ]
        
        # Add baseline memories
        now = datetime.datetime.now()
        for memory in baseline_memories:
            app_tables.memories.add_row(
                memory_type=memory["memory_type"],
                key=memory["key"],
                value=memory["value"],
                created_at=now,
                updated_at=now,
                importance=8,
                source="initialization",
                is_expired=False
            )
            
        return {"status": "Memory system initialized with baseline memories"}
    else:
        return {"status": "Memory system already initialized"}