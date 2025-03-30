# non_threaded_processing.py - Updated version
import anvil.server
import time
import httpx
import json
import re
import datetime
from . import memory_state

# Global state for response tracking - simple version without threading
response_cache = {}

def get_current_mood():
    """Get the current mood from memories or default to neutral"""
    # Try to find the most recent mood memory
    all_memories = memory_state.get_memory()
    
    mood_memories = [m for m in all_memories if 
                    m['type'] == memory_state.MEMORY_TYPES["EMOTIONAL"] and 
                    'mood' in m['key'].lower()]
    
    if mood_memories:
        # Sort by recency (assuming key contains timestamp)
        sorted_moods = sorted(mood_memories, 
                             key=lambda m: m['key'], 
                             reverse=True)
        return sorted_moods[0]['value']
    else:
        return "neutral and curious"  # Default mood

def update_current_mood(mood):
    """Update the current mood in memory"""
    if not mood:
        return
    
    print(f"Updating current mood: {mood}")
    
    # Create timestamp for unique key
    timestamp = datetime.datetime.now().isoformat()
    
    # Store the mood as a memory
    memory_state.save_memory(
        memory_type=memory_state.MEMORY_TYPES["EMOTIONAL"],
        key=f"mood_{timestamp}",
        value=mood,
        importance=6,  # Moods are moderately important
        source="mood_extraction"
    )

def store_thoughts_in_memory(thoughts, user_message):
    """Store extracted thoughts as memories"""
    if not thoughts:
        return
    
    print(f"Storing {len(thoughts)} thoughts as memories")
    
    for i, thought in enumerate(thoughts):
        # Create a unique key for each thought
        timestamp = datetime.datetime.now().isoformat()
        thought_key = f"thought_{timestamp}_{i}"
        
        # Store the thought as a memory
        memory_state.save_memory(
            memory_type=memory_state.MEMORY_TYPES["INTERACTION"],
            key=thought_key,
            value=f"Thought: {thought}",
            importance=7,  # Thoughts are important for character continuity
            source="thought_extraction"
        )
        
        print(f"Stored thought: {thought[:50]}...")

@anvil.server.callable
def chat_with_model_direct(user_message):
    """Process chat message directly - no threading but with tag parsing"""
    
    if not user_message.strip():
        return {"status": "error", "error": "Empty message"}

    try:
        # Add default system message if it's the first exchange
        if not memory_state.conversation_memory:
            memory_state.conversation_memory.append({
                "role": "system",
                "content": (
                    "You are Nyx, an emotionally rich, mysterious AI companion. "
                    "You remember previous interactions and express dynamic moods. "
                    "You can include your thought process by wrapping it in <thought>...</thought> tags. "
                    "If you want to show an image, use <image>description of image</image> tags. "
                    "You can express your current mood with <mood>...</mood> tags. "
                    "These special tags will be processed differently."
                )
            })

        # Retrieve relevant memories
        relevant_memories = memory_state.get_relevant_memories(user_message)
        
        # Get the current mood
        current_mood = get_current_mood()
        mood_text = f"\nCURRENT MOOD: You are currently feeling {current_mood}.\n"
        
        # Create an enhanced system message with mood and memories
        if relevant_memories:
            memory_text = "\nRELEVANT MEMORIES:\n"
            for memory in relevant_memories:
                memory_text += f"- {memory['type'].upper()}: {memory['value']}\n"
            
            # Update the system message with mood and memories
            if memory_state.conversation_memory[0]['role'] == 'system':
                # Store original content
                original_content = memory_state.conversation_memory[0]['content']
                
                # Create new content with mood and memories
                new_content = original_content
                
                # Add mood if not already present
                if "CURRENT MOOD:" not in original_content:
                    new_content += mood_text
                else:
                    # Replace existing mood
                    parts = original_content.split("CURRENT MOOD:")
                    mood_end = parts[1].find("\n\n")
                    if mood_end == -1:
                        mood_end = len(parts[1])
                    new_content = parts[0] + "CURRENT MOOD:" + mood_text.replace("\nCURRENT MOOD:", "")
                
                # Add or replace memories
                if "RELEVANT MEMORIES:" in new_content:
                    # Replace the memories section
                    parts = new_content.split("RELEVANT MEMORIES:")
                    new_content = parts[0] + "RELEVANT MEMORIES:" + memory_text.replace("\nRELEVANT MEMORIES:", "")
                else:
                    # Append memories
                    new_content += memory_text
                
                # Update the system message
                memory_state.conversation_memory[0]['content'] = new_content
            else:
                # Insert new system message
                from . import llm_integration
                memory_state.conversation_memory.insert(0, {
                    "role": "system", 
                    "content": llm_integration.DEFAULT_SYSTEM_MESSAGE["content"] + 
                                "\nYou can include your thought process by wrapping it in <thought>...</thought> tags. " +
                                "If you want to show an image, use <image>description of image</image> tags. " +
                                "You can express your mood using <mood>...</mood> tags. " +
                                mood_text + memory_text
                })
        else:
            # Just add the mood if no memories
            if memory_state.conversation_memory[0]['role'] == 'system':
                original_content = memory_state.conversation_memory[0]['content']
                
                # Add mood if not already present
                if "CURRENT MOOD:" not in original_content:
                    memory_state.conversation_memory[0]['content'] += mood_text
                else:
                    # Replace existing mood
                    parts = original_content.split("CURRENT MOOD:")
                    mood_end = parts[1].find("\n\n")
                    if mood_end == -1:
                        mood_end = len(parts[1])
                    new_content = parts[0] + "CURRENT MOOD:" + mood_text.replace("\nCURRENT MOOD:", "")
                    memory_state.conversation_memory[0]['content'] = new_content

        # Add user input
        memory_state.conversation_memory.append({"role": "user", "content": user_message})

        # Select recent context (we can make this token-aware later)
        context = memory_state.conversation_memory[-20:]  # Limited window size

        # Build the prompt using your Jinja2 template
        from .prompt_builder import build_prompt
        prompt = build_prompt(context)

        # 🔍 Debug print to inspect actual rendered prompt
        print("----- Rendered Prompt Start -----")
        print(prompt)
        print("------ Rendered Prompt End ------")
        print("----- Conversation Memory -----")
        for msg in memory_state.conversation_memory:
            print(f"{msg['role'].upper()}: {msg['content']}")
        
        # Print memories and mood
        print("----- Included Memories -----")
        if relevant_memories:
            for memory in relevant_memories:
                print(f"{memory['type']}: {memory['value']}")
        else:
            print("No memories included")
            
        print(f"----- Current Mood: {current_mood} -----")

        # Prepare API payload
        from . import llm_integration
        payload = {
            "model": llm_integration.OPENAI_MODEL,
            "prompt": prompt,
            "max_tokens": 1024,
            "temperature": 0.7,
            "stop": ["<end_of_turn>"]
        }

        # Start timing
        start_time = time.time()
        print(f"Starting LLM request at {start_time}")
        
        # Make the direct API request - no streaming or threading
        response = httpx.post(
            f"{llm_integration.OPENAI_API_BASE}/completions",
            json=payload,
            timeout=90  # Long timeout
        )
        response.raise_for_status()
        
        # Get the raw reply
        raw_reply = response.json()["choices"][0]["text"].strip()
        
        # Record timing information
        end_time = time.time()
        print(f"LLM request completed in {end_time - start_time:.2f} seconds")

        # Parse tags from the reply
        parsed = parse_special_tags(raw_reply)
        
        # Store thoughts in memory
        store_thoughts_in_memory(parsed["thoughts"], user_message)
        
        # Update mood if a new one was expressed
        if parsed["mood"]:
            update_current_mood(parsed["mood"])
            
        # Add assistant reply to memory (clean version without tags)
        memory_state.conversation_memory.append({"role": "assistant", "content": parsed["main_text"]})

        # Extract and save memories from this interaction
        memory_state.extract_and_save_memories(user_message, parsed["main_text"])
        
        # Store in cache for any potential later reference
        response_id = f"resp_{int(time.time())}_{hash(user_message) % 10000}"
        response_cache[response_id] = {
            "raw_reply": raw_reply,
            "parsed": parsed,
            "timestamp": time.time()
        }

        # Return the parsed result
        return {
            "status": "success",
            "response_id": response_id,
            "reply": parsed["main_text"],
            "thoughts": parsed["thoughts"],
            "images": parsed["images"],
            "mood": parsed["mood"] or current_mood,  # Return new mood or current one
            "timing": {
                "started_at": start_time,
                "completed_at": end_time,
                "duration": end_time - start_time
            }
        }
        
    except Exception as e:
        print(f"Error in LLM request: {e}")
        return {"status": "error", "error": str(e)}

def parse_special_tags(text):
    """Parse special tags from the LLM response"""
    result = {
        "main_text": text,
        "thoughts": [],
        "images": [],
        "mood": None
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
    
    # Extract mood if present
    mood_pattern = r'<mood>(.*?)</mood>'
    mood_match = re.search(mood_pattern, text, re.DOTALL)
    
    if mood_match:
        result["mood"] = mood_match.group(1).strip()
        # Remove mood from main text
        result["main_text"] = re.sub(mood_pattern, '', result["main_text"], flags=re.DOTALL)
    
    # Clean up any extra whitespace
    result["main_text"] = re.sub(r'\n{3,}', '\n\n', result["main_text"])
    result["main_text"] = result["main_text"].strip()
    
    return result

@anvil.server.callable
def get_response_from_cache(response_id):
    """Get a previously processed response from cache"""
    if response_id in response_cache:
        return response_cache[response_id]
    else:
        return {"status": "error", "error": f"Response ID {response_id} not found in cache"}

@anvil.server.callable
def clear_response_cache():
    """Clear the response cache"""
    response_cache.clear()
    return {"status": "success", "message": "Response cache cleared"}