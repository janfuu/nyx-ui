# background_processing.py
import anvil.server
import threading
import time
import httpx
import json
import re
from . import memory_state

# Global state for response tracking
response_state = {
    "status": "idle",  # idle, processing, complete, error
    "response_id": None,
    "raw_reply": "",
    "parsed_reply": {
        "main_text": "",
        "thoughts": [],
        "images": [],
        "additional_data": {}
    },
    "error": None,
    "started_at": None,
    "completed_at": None
}

# Thread-safe lock for updating the response state
state_lock = threading.Lock()

# Store active response tasks
active_tasks = {}

@anvil.server.callable
def start_chat_processing(user_message, response_id=None):
    """Start processing a chat message in the background"""
    global response_state
    
    # Generate a response ID if none provided
    if response_id is None:
        response_id = f"resp_{int(time.time())}_{hash(user_message) % 10000}"
    
    with state_lock:
        # Reset response state
        response_state = {
            "status": "processing",
            "response_id": response_id,
            "raw_reply": "",
            "parsed_reply": {
                "main_text": "",
                "thoughts": [],
                "images": [],
                "additional_data": {}
            },
            "error": None,
            "started_at": time.time(),
            "completed_at": None
        }
    
    # Start a background thread for processing
    thread = threading.Thread(
        target=_process_chat_message, 
        args=(user_message, response_id),
        daemon=True
    )
    thread.start()
    
    # Store the active task
    active_tasks[response_id] = {
        "thread": thread,
        "user_message": user_message,
        "started_at": time.time()
    }
    
    return {"status": "started", "response_id": response_id}

@anvil.server.callable
def get_response_state(response_id=None):
    """Get the current state of the response processing"""
    global response_state
    
    with state_lock:
        # If a specific response_id is requested, check if it matches
        if response_id is not None and response_id != response_state["response_id"]:
            return {
                "status": "unknown",
                "error": f"Response ID {response_id} not found or expired"
            }
        
        # Return a copy of the current state
        return dict(response_state)

@anvil.server.callable
def cancel_processing(response_id=None):
    """Cancel a running process (limited capability)"""
    global response_state
    
    # We can't truly kill a thread in Python, but we can mark it as cancelled
    with state_lock:
        if response_state["status"] == "processing":
            response_state["status"] = "idle"
            response_state["error"] = "Cancelled by user"
            
    # Remove from active tasks
    if response_id and response_id in active_tasks:
        del active_tasks[response_id]
            
    return {"status": "cancelled"}

def _process_chat_message(user_message, response_id):
    """Process the chat message in a background thread"""
    try:
        # Call the chat model
        from . import llm_integration
        
        # Build prompt with memories
        if not memory_state.conversation_memory:
            memory_state.conversation_memory.append({
                "role": "system",
                "content": (
                    "You are Nyx, an emotionally rich, mysterious AI companion. "
                    "You remember previous interactions and express dynamic moods. "
                    "You can include your thought process by wrapping it in <thought>...</thought> tags. "
                    "If you want to show an image, use <image>description of image</image> tags. "
                    "These special tags will be processed differently."
                )
            })

        # Get relevant memories
        relevant_memories = memory_state.get_relevant_memories(user_message)
        
        # Add memories to system message
        if relevant_memories:
            memory_text = "\nRELEVANT MEMORIES:\n"
            for memory in relevant_memories:
                memory_text += f"- {memory['type'].upper()}: {memory['value']}\n"
            
            if memory_state.conversation_memory[0]['role'] == 'system':
                # Check if there's already a RELEVANT MEMORIES section
                if "RELEVANT MEMORIES:" in memory_state.conversation_memory[0]['content']:
                    # Replace the existing section
                    parts = memory_state.conversation_memory[0]['content'].split("RELEVANT MEMORIES:")
                    memory_state.conversation_memory[0]['content'] = parts[0] + "RELEVANT MEMORIES:" + memory_text
                else:
                    # Append to existing message
                    memory_state.conversation_memory[0]['content'] += memory_text
            else:
                # Insert new system message
                memory_state.conversation_memory.insert(0, {
                    "role": "system",
                    "content": llm_integration.DEFAULT_SYSTEM_MESSAGE["content"] + 
                              "\nYou can include your thought process by wrapping it in <thought>...</thought> tags. " +
                              "If you want to show an image, use <image>description of image</image> tags. " +
                              memory_text
                })

        # Add user message to conversation
        memory_state.conversation_memory.append({"role": "user", "content": user_message})

        # Select recent context
        context = memory_state.conversation_memory[-20:]  # Limited window size

        # Build prompt
        from .prompt_builder import build_prompt
        prompt = build_prompt(context)

        # Debug info
        print(f"----- Prompt for {response_id} -----")
        print(prompt)
        print("----- Memories included -----")
        if relevant_memories:
            for memory in relevant_memories:
                print(f"{memory['type']}: {memory['value']}")
        else:
            print("No memories included")

        # Prepare API payload
        payload = {
            "model": llm_integration.OPENAI_MODEL,
            "prompt": prompt,
            "max_tokens": 1024,
            "temperature": 0.7,
            "stop": ["<end_of_turn>"]
        }

        # Make the API request
        start_time = time.time()
        print(f"Starting LLM request for {response_id} at {start_time}")
        
        response = httpx.post(
            f"{llm_integration.OPENAI_API_BASE}/completions",
            json=payload,
            timeout=90  # Longer timeout
        )
        response.raise_for_status()
        
        # Get the raw reply
        raw_reply = response.json()["choices"][0]["text"].strip()
        
        # Update state with raw reply
        with state_lock:
            response_state["raw_reply"] = raw_reply
        
        # Parse the tags in the reply
        parsed_reply = parse_response_tags(raw_reply)
        
        # Update the state with the parsed reply
        with state_lock:
            response_state["status"] = "complete"
            response_state["parsed_reply"] = parsed_reply
            response_state["completed_at"] = time.time()
        
        # Add assistant response to memory
        # We add the clean, main text without special tags
        memory_state.conversation_memory.append({
            "role": "assistant", 
            "content": parsed_reply["main_text"]
        })
        
        # Extract memories from this interaction
        memory_state.extract_and_save_memories(user_message, parsed_reply["main_text"])
        
        # Log completion
        end_time = time.time()
        print(f"Completed LLM request for {response_id} in {end_time - start_time:.2f} seconds")
        
        # Clean up
        if response_id in active_tasks:
            del active_tasks[response_id]
            
    except Exception as e:
        # Update state with error
        with state_lock:
            response_state["status"] = "error"
            response_state["error"] = str(e)
            response_state["completed_at"] = time.time()
        
        print(f"Error processing chat for {response_id}: {e}")
        
        # Clean up
        if response_id in active_tasks:
            del active_tasks[response_id]

def parse_response_tags(text):
    """Parse special tags in the LLM response"""
    result = {
        "main_text": text,
        "thoughts": [],
        "images": [],
        "additional_data": {}
    }
    
    # Extract thoughts
    thought_pattern = r'<thought>(.*?)</thought>'
    thought_matches = re.finditer(thought_pattern, text, re.DOTALL)
    
    for match in thought_matches:
        thought_text = match.group(1).strip()
        result["thoughts"].append(thought_text)
        
    # Remove thoughts from main text
    result["main_text"] = re.sub(thought_pattern, '', result["main_text"], flags=re.DOTALL)
    
    # Extract image requests
    image_pattern = r'<image>(.*?)</image>'
    image_matches = re.finditer(image_pattern, text, re.DOTALL)
    
    for match in image_matches:
        image_desc = match.group(1).strip()
        result["images"].append(image_desc)
        
    # Replace image tags with placeholders in main text
    result["main_text"] = re.sub(image_pattern, '[Image: \\1]', result["main_text"], flags=re.DOTALL)
    
    # Clean up any extra whitespace
    result["main_text"] = re.sub(r'\n{3,}', '\n\n', result["main_text"])
    result["main_text"] = result["main_text"].strip()
    
    return result