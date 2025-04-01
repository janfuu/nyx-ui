from ._anvil_designer import Form1Template
from anvil import *
import anvil.server
import anvil.http

class Form1(Form1Template):

  def __init__(self, **properties):
    self.init_components(**properties)
    self._last_location = None
    self.current_image_description = None

  def timer_image_check_tick(self, **event_args):
    """Poll Runware background image task"""
    try:
      if not self.image_task_id:
        self.timer_image_check.enabled = False
        return

      with anvil.server.no_loading_indicator:
        result = anvil.server.call('check_image_task', self.image_task_id)

      if result.get("status") == "error":
        print("Image generation failed:", result.get("error"))
        self.timer_image_check.enabled = False
        return

      if result.get("is_completed"):
        self.timer_image_check.enabled = False
        final = result.get("result")
        if final and final.get("image_url"):
          self.image_generated.source = final["image_url"]
        else:
          print("Image task completed but no image returned")

    except Exception as e:
      print(f"Polling error: {e}")
      self.timer_image_check.enabled = False


  def button_send_click(self, **event_args):
    print("Button clicked")  # Confirm this actually fires
    user_msg = self.text_box_input.text
    
    if not user_msg.strip():
      return
      
    self.text_area_chat.text += f"You: {user_msg}\n"
    self.text_box_input.text = ''

    try:
      # Show a "thinking" indicator
      self.text_area_chat.text += f"Nyx: Thinking...\n"
      
      # Use the direct processing function
      result = anvil.server.call('chat_pipeline', user_msg)
      
      if result["status"] == "success":
        # Update chat area - remove "Thinking..." and add the response
        chat_lines = self.text_area_chat.text.split('\n')
        if "Nyx: Thinking..." in chat_lines[-1]:
          chat_lines = chat_lines[:-1]  # Remove the last line
        
        chat_lines.append(f"Nyx: {result['reply']}")
        self.text_area_chat.text = '\n'.join(chat_lines)
        
        # Update thoughts area if any thoughts were extracted
        if result.get("thoughts"):
          self.text_area_thoughts.text = '\n\n'.join(result["thoughts"])
        
        # Update mood indicator
        if result.get("mood"):
          self.label_mood.text = result["mood"]
        else:
          self.label_mood.text = "Normal"  # Default mood
        
        # Handle image generation if any image requests were found
        if result.get("images"):
          self.handle_image_generation(result["images"][0])
        
      else:
        # Error occurred
        chat_lines = self.text_area_chat.text.split('\n')
        if "Nyx: Thinking..." in chat_lines[-1]:
          chat_lines = chat_lines[:-1]  # Remove the last line
        
        chat_lines.append(f"Error: {result['error']}")
        self.text_area_chat.text = '\n'.join(chat_lines)
        self.label_mood.text = "Error"
        
    except Exception as e:
      # Update chat to show error
      chat_lines = self.text_area_chat.text.split('\n')
      if "Nyx: Thinking..." in chat_lines[-1]:
        chat_lines = chat_lines[:-1]  # Remove the last line
      
      chat_lines.append(f"Error: {e}")
      self.text_area_chat.text = '\n'.join(chat_lines)
      self.label_mood.text = "Error"

  def handle_image_generation(self, image_description):
    self.current_image_description = image_description
    try:
      with anvil.server.no_loading_indicator:
        task_id = anvil.server.call('launch_image_task', image_description)

      self.image_task_id = task_id
      self.timer_image_check.enabled = True
    except Exception as e:
      print(f"Image task launch failed: {e}")


  def timer_image_check_tick(self, **event_args):
    """Poll Runware background image task"""
    try:
        if not self.image_task_id:
            self.timer_image_check.enabled = False
            return

        result = anvil.server.call('check_image_task', self.image_task_id)

        if result.get("status") == "error":
            print("Image generation failed:", result.get("error"))
            self.timer_image_check.enabled = False
            return

        if result.get("is_completed"):
            self.timer_image_check.enabled = False
            final = result.get("result")
            if final and final.get("image_url"):
                self.image_generated.source = final["image_url"]
            else:
                print("Image task completed but no image returned")

    except Exception as e:
        print(f"Polling error: {e}")
        self.timer_image_check.enabled = False


  def display_generated_image(self, result):
    if result["status"] == "success":
        if result.get("image_url"):
            self.image_generated.source = result["image_url"]
        elif result.get("image_data"):
            try:
                import base64
                from anvil import BlobMedia
                decoded = base64.b64decode(result["image_data"])
                self.image_generated.source = BlobMedia("image/png", decoded)
            except:
                print("Failed to decode base64 image data")
    else:
        print("Image generation failed or no image returned")
        # DO NOT change the image component — leave as-is



  def button_generate_image_click(self, **event_args):
    """Generate image from current description"""
    if self.current_image_description:
      self.handle_image_generation(self.current_image_description)
    else:
      alert("No image description available. Ask Nyx to create an image first.")

  def text_box_input_pressed_enter(self, **event_args):
    self.button_send_click()

  def check_table_btn_click(self, **event_args):
    """Check if memories table exists and create it if not"""
    result = anvil.server.call('ensure_memories_table_exists')
    alert(f"Table status: {result['status']}")

  def init_memory_btn_click(self, **event_args):
    """Initialize test memories"""
    result = anvil.server.call('initialize_memory_system')
    alert(f"Memory system: {result['status']}")

  def debug_memory_btn_click(self, **event_args):
    """Print all stored memories"""
    result = anvil.server.call('print_all_memories')
    alert(f"Found {result['count']} memories. Check server logs for details.")

  def force_memory_btn_click(self, **event_args):
    """Force memories to be included in next prompt"""
    result = anvil.server.call('force_memory_inclusion')
    if result['status'] == 'success':
      alert(f"Added {result['memories_included']} memories to system prompt")
    else:
      alert(f"Error: {result['message']}")