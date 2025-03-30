# tag_processing.py
import anvil.server
import re
import json
import httpx
import base64
from io import BytesIO
try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# Define possible tags with handlers
TAG_HANDLERS = {
    "thought": "process_thought_tag",
    "image": "process_image_tag",
    "code": "process_code_tag",
    "emotion": "process_emotion_tag",
    "memory": "process_memory_tag"
}

@anvil.server.callable
def process_special_tags(parsed_response):
    """Process all special tags in the parsed response"""
    result = {
        "main_text": parsed_response["main_text"],
        "processed_elements": [],
        "errors": []
    }
    
    # Process thoughts
    for thought in parsed_response.get("thoughts", []):
        try:
            thought_result = process_thought_tag(thought)
            result["processed_elements"].append({
                "type": "thought",
                "content": thought_result
            })
        except Exception as e:
            result["errors"].append(f"Error processing thought: {e}")
    
    # Process images
    for image_desc in parsed_response.get("images", []):
        try:
            image_result = process_image_tag(image_desc)
            result["processed_elements"].append({
                "type": "image",
                "description": image_desc,
                "content": image_result
            })
        except Exception as e:
            result["errors"].append(f"Error processing image: {e}")
            # Add fallback text for the image
            result["main_text"] += f"\n\n[Image generation failed: {image_desc}]"
    
    return result

def process_thought_tag(thought_content):
    """Process content inside <thought> tags"""
    # You could enhance this with additional formatting or processing
    return {
        "raw_content": thought_content,
        "formatted_content": thought_content,
        "meta": {
            "timestamp": anvil.server.call('anvil.server.get_app_origin_timestamp'),
            "is_visible": True  # Whether to show thoughts to the user
        }
    }

def process_image_tag(image_description):
    """Process content inside <image> tags - generate an image"""
    # This is a placeholder for actual image generation logic
    # You would integrate with an image generation service here
    
    try:
        # Placeholder for actual image generation API call
        # Example using a hypothetical API (replace with your actual implementation)
        """
        response = httpx.post(
            "https://your-image-generation-api.com/generate",
            json={
                "prompt": image_description,
                "style": "realistic",
                "width": 512,
                "height": 512
            },
            timeout=30
        )
        response.raise_for_status()
        image_data = response.json()
        """
        
        # Placeholder for now - you would implement actual image generation
        print(f"Would generate image for: {image_description}")
        
        return {
            "description": image_description,
            "status": "placeholder",  # Would be "generated" with a real API
            "url": None,  # Would be the URL to the generated image
            "meta": {
                "requested_at": anvil.server.call('anvil.server.get_app_origin_timestamp'),
                "generation_params": {
                    "prompt": image_description,
                    "model": "placeholder"
                }
            }
        }
    except Exception as e:
        print(f"Error generating image: {e}")
        return {
            "description": image_description,
            "status": "error",
            "error": str(e)
        }

@anvil.server.callable
def process_code_tag(code_content, language=None):
    """Process content inside <code> tags"""
    # Extract language if specified in the opening tag
    if language is None and "```" in code_content:
        # Try to extract language from markdown code blocks
        match = re.match(r"```(\w+)\n", code_content)
        if match:
            language = match.group(1)
            # Remove the language specifier
            code_content = re.sub(r"```\w+\n", "```\n", code_content)
    
    return {
        "code": code_content,
        "language": language,
        "formatted_content": code_content
    }

@anvil.server.callable
def process_emotion_tag(emotion_content):
    """Process content inside <emotion> tags"""
    emotions = {
        "happy": "😊",
        "sad": "😢",
        "angry": "😠",
        "surprised": "😮",
        "thoughtful": "🤔",
        "excited": "😃",
        "calm": "😌",
        "worried": "😟",
        "confused": "😕",
        "amused": "😏"
    }
    
    emotion_lower = emotion_content.lower().strip()
    emoji = emotions.get(emotion_lower, "")
    
    return {
        "emotion": emotion_lower,
        "emoji": emoji,
        "intensity": 1.0,  # Could parse intensity if provided
        "display": f"{emotion_content} {emoji}"
    }

@anvil.server.callable
def process_memory_tag(memory_content):
    """Process content inside <memory> tags to create a new memory"""
    from . import memory_state
    
    # Parse the memory content
    # Expected format: <memory type="TYPE" key="KEY">VALUE</memory>
    memory_type_match = re.search(r'type="([^"]+)"', memory_content)
    memory_key_match = re.search(r'key="([^"]+)"', memory_content)
    
    # Extract the value (everything else in the tag)
    memory_value = re.sub(r'type="[^"]+"', '', memory_content)
    memory_value = re.sub(r'key="[^"]+"', '', memory_value).strip()
    
    if memory_type_match and memory_value:
        memory_type = memory_type_match.group(1)
        
        # If key is specified, use it, otherwise generate one
        if memory_key_match:
            memory_key = memory_key_match.group(1)
        else:
            import datetime
            memory_key = f"{memory_type}_{datetime.datetime.now().isoformat()}"
        
        # Save to memory system
        try:
            memory_state.save_memory(
                memory_type=memory_type,
                key=memory_key,
                value=memory_value
            )
            return {
                "status": "saved",
                "type": memory_type,
                "key": memory_key,
                "value": memory_value
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    else:
        return {
            "status": "error",
            "error": "Invalid memory format. Expected: <memory type=\"TYPE\" key=\"KEY\">VALUE</memory>"
        }

@anvil.server.callable
def parse_all_tags(text):
    """Parse all recognized tags in a piece of text"""
    result = {
        "main_text": text,
        "found_tags": []
    }
    
    # Process all defined tags
    for tag_name, handler_name in TAG_HANDLERS.items():
        pattern = f"<{tag_name}>(.*?)</{tag_name}>"
        tag_matches = re.finditer(pattern, text, re.DOTALL)
        
        for match in tag_matches:
            tag_content = match.group(1).strip()
            result["found_tags"].append({
                "type": tag_name,
                "content": tag_content,
                "handler": handler_name,
                "span": (match.start(), match.end())
            })
    
    # Sort tags by their position in the text
    result["found_tags"].sort(key=lambda x: x["span"][0])
    
    return result

@anvil.server.callable
def extract_and_process_response(text):
    """One-step function to extract all tags and process them"""
    # First parse all tags
    parsed = parse_all_tags(text)
    
    # Initialize result with clean main text
    result = {
        "main_text": text,
        "processed_tags": []
    }
    
    # Process each tag with its handler
    for tag in parsed["found_tags"]:
        try:
            # Get the handler function
            handler_name = tag["handler"]
            if handler_name in globals():
                handler_func = globals()[handler_name]
                
                # Call the handler
                processed = handler_func(tag["content"])
                
                # Add to results
                result["processed_tags"].append({
                    "type": tag["type"],
                    "original": tag["content"],
                    "processed": processed
                })
                
                # Remove tag from main text
                pattern = f"<{tag['type']}>{re.escape(tag['content'])}</{tag['type']}>"
                result["main_text"] = re.sub(pattern, '', result["main_text"], flags=re.DOTALL)
        except Exception as e:
            print(f"Error processing tag {tag['type']}: {e}")
    
    # Clean up whitespace
    result["main_text"] = re.sub(r'\n{3,}', '\n\n', result["main_text"])
    result["main_text"] = result["main_text"].strip()
    
    return result