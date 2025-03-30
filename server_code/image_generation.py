# image_generation.py
import anvil.server
import httpx
import json
import base64
import os
from io import BytesIO

# Configure the Runware SDK settings
# You'll need to adjust these settings based on your Runware setup
RUNWARE_API_URL = "https://api.runware.ai/v1"  # Change to your Runware API endpoint
RUNWARE_API_KEY = os.environ.get("RUNWARE_API_KEY", "your_default_api_key")

class ImageGenerationError(Exception):
    """Custom exception for image generation errors"""
    pass

@anvil.server.callable
def generate_image(prompt, width=512, height=512, model="sd3"):
    """
    Generate an image using the Runware SDK
    
    Args:
        prompt (str): The image description to generate
        width (int): Image width
        height (int): Image height
        model (str): Model to use for generation
        
    Returns:
        dict: Contains the image URL or data
    """
    try:
        print(f"Generating image for prompt: {prompt}")
        
        # Prepare the payload for Runware SDK
        payload = {
            "prompt": prompt,
            "width": width,
            "height": height,
            "model": model,
            "num_inference_steps": 30,
            "guidance_scale": 7.5
        }
        
        # Set up headers with API key if required
        headers = {}
        if RUNWARE_API_KEY:
            headers["Authorization"] = f"Bearer {RUNWARE_API_KEY}"
        
        print("Sending request to Runware SDK...")
        
        # Make the API request
        response = httpx.post(
            RUNWARE_API_URL,
            json=payload,
            headers=headers,
            timeout=120  # Image generation can take time
        )
        
        # Check for errors
        response.raise_for_status()
        
        # Parse the response
        result = response.json()
        
        if "error" in result:
            raise ImageGenerationError(f"Runware SDK error: {result['error']}")
        
        print("Image generation successful")
        
        # Return the result
        # The structure depends on the Runware SDK response format
        # This is a placeholder - adjust based on actual response format
        return {
            "status": "success",
            "image_url": result.get("image_url"),
            "image_data": result.get("image_data"),
            "prompt": prompt
        }
        
    except httpx.HTTPStatusError as e:
        print(f"HTTP error: {e.response.status_code} - {e.response.text}")
        return {
            "status": "error",
            "error": f"HTTP error: {e.response.status_code}",
            "details": e.response.text
        }
    except httpx.RequestError as e:
        print(f"Request error: {str(e)}")
        return {
            "status": "error",
            "error": f"Request error: {str(e)}"
        }
    except ImageGenerationError as e:
        print(f"Generation error: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return {
            "status": "error",
            "error": f"Unexpected error: {str(e)}"
        }

@anvil.server.callable
def handle_image_tag(image_description):
    """Process an image tag and generate the image"""
    # Generate the image
    result = generate_image(image_description)
    
    if result["status"] == "success":
        # Image generation successful
        if result.get("image_url"):
            # If Runware returns a URL
            return {
                "status": "success",
                "image_url": result["image_url"],
                "prompt": image_description
            }
        elif result.get("image_data"):
            # If Runware returns base64 image data
            # In Anvil, you might need to handle this differently
            return {
                "status": "success",
                "image_data": result["image_data"],
                "prompt": image_description
            }
    else:
        # Image generation failed
        return {
            "status": "error",
            "error": result["error"],
            "prompt": image_description
        }

# Alternative more flexible implementation that can be adjusted based on Runware SDK
@anvil.server.callable
def generate_image_with_sdk(prompt, **params):
    """
    Flexible image generation function that can be adjusted for different Runware SDK implementations
    
    Args:
        prompt (str): The image description
        **params: Additional parameters to pass to the SDK
        
    Returns:
        dict: Contains the image result
    """
    # This is a placeholder - you'll need to implement this based on your Runware SDK
    try:
        # This is where you'd implement the actual Runware SDK integration
        # SDK might look something like:
        # from runware import ImageGenerator
        # generator = ImageGenerator(api_key=RUNWARE_API_KEY)
        # result = generator.generate(prompt, **params)
        
        # Placeholder for now
        print(f"Would generate image with Runware SDK: {prompt}")
        print(f"Parameters: {params}")
        
        # Simulated response
        return {
            "status": "success",
            "image_url": "https://placeholder.com/image.jpg",  # This would be the actual image URL
            "prompt": prompt
        }
        
    except Exception as e:
        print(f"Error with Runware SDK: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }