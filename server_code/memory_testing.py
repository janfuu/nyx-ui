# memory_testing.py
import anvil.server
from . import memory_state

@anvil.server.callable
def initialize_test_memories():
    """Create some test memories to verify the system is working"""
    # Clear existing memories for testing
    memory_state.local_memory_storage.clear()
    
    # Add some test memories
    test_memories = [
        {
            "memory_type": memory_state.MEMORY_TYPES["FACTUAL"],
            "key": "name",
            "value": "The user's name is Alex."
        },
        {
            "memory_type": memory_state.MEMORY_TYPES["PREFERENCE"],
            "key": "preference_music",
            "value": "The user enjoys jazz and classical music."
        },
        {
            "memory_type": memory_state.MEMORY_TYPES["EMOTIONAL"],
            "key": "emotion_recent",
            "value": "The user mentioned feeling nostalgic recently."
        },
        {
            "memory_type": memory_state.MEMORY_TYPES["INTERACTION"],
            "key": "interaction_pattern",
            "value": "The user tends to write in poetic language."
        }
    ]
    
    # Save test memories
    for memory in test_memories:
        memory_state.save_memory(
            memory_type=memory["memory_type"],
            key=memory["key"],
            value=memory["value"],
            importance=8
        )
    
    return {"status": "success", "count": len(test_memories)}


@anvil.server.callable
def print_all_memories():
    """Debug function to print all stored memories"""
    all_memories = memory_state.get_memory()
    
    print("----- ALL STORED MEMORIES -----")
    for i, memory in enumerate(all_memories):
        print(f"{i+1}. {memory['type']}: {memory['key']} = {memory['value']}")
    
    return {"count": len(all_memories), "memories": all_memories}


@anvil.server.callable
def force_memory_inclusion():
    """Force the system to include memories in the next prompt"""
    
    # Modify system message to mention memories explicitly
    if memory_state.conversation_memory and memory_state.conversation_memory[0]['role'] == 'system':
        # Get all memories
        all_memories = memory_state.get_memory()
        
        # Add memories to system message
        memory_text = "\n\nIMPORTANT CONTEXT - WHAT I KNOW ABOUT YOU:\n"
        for memory in all_memories:
            memory_text += f"- {memory['value']}\n"
        
        # Update system message
        original_content = memory_state.conversation_memory[0]['content']
        if "IMPORTANT CONTEXT" not in original_content:
            memory_state.conversation_memory[0]['content'] = original_content + memory_text
            
        return {"status": "success", "memories_included": len(all_memories)}
    else:
        return {"status": "error", "message": "No system message found"}