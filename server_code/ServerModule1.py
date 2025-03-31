import anvil.server
from anvil.tables import app_tables
import datetime
# from . import background_processing
# from . import tag_processing
from . import memory_state
from . import non_threaded_processing
from . import image_generation
from . import pipeline
import threading
import time

# For handling background image generation
image_tasks = {}

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


@anvil.server.callable
def chat_pipeline(user_message):
    """Process a chat message directly with tag parsing"""
    return non_threaded_processing.chat_with_model_direct(user_message)

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
    

@anvil.server.callable
def generate_image_for_tag(image_description):
    """Generate an image directly from the UI"""
    return image_generation.handle_image_tag(image_description)

@anvil.server.callable
def background_generate_image(image_description, callback=None):
    """Generate an image in the background with optional callback"""
    # Don't use threading if running locally due to potential issues
    # Just generate directly
    result = image_generation.handle_image_tag(image_description)
    
    # If callback is provided, call it with the result
    if callback:
        callback(result)
    
    return result

# Add this to the non_threaded_processing.py module
def process_image_tags_after_response(parsed_response):
    """Process any image tags in the response after sending the text reply"""
    if not parsed_response.get("images"):
        return
    
    for image_desc in parsed_response["images"]:
        try:
            # Generate the image in the background
            print(f"Processing image tag: {image_desc}")
            anvil.server.call('background_generate_image', image_desc)
        except Exception as e:
            print(f"Error processing image tag: {e}")

# Modify the chat_with_model_direct function to initiate image generation:
# Add this at the end of the function, after returning the text response:
"""
# Initiate image generation in background if needed
if parsed["images"]:
    # Start generating the images after returning the text response
    # This happens asynchronously
    process_image_tags_after_response(parsed)
"""