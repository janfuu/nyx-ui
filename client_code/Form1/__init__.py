from ._anvil_designer import Form1Template
from anvil import *
import anvil.server
import anvil.http

API_BASE = 'http://localhost:8000/api'

class Form1(Form1Template):

  def __init__(self, **properties):
    self.init_components(**properties)
    self._last_location = None
    self.timer_1.interval = 30
    self.current_image_description = None

  def timer_1_tick(self, **event_args):
    #  self.update_all_cards()
    pass

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
      result = anvil.server.call('chat_with_model_direct', user_msg)
      
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
    """Handle image generation process"""
    # Update image description
    self.label_image_desc.text = image_description
    self.current_image_description = image_description
    
    # Show loading indicator for image
    self.image_1.source = "https://via.placeholder.com/300x300.png?text=Generating+Image..."
    
    # Generate image in background
    anvil.server.call_s('background_generate_image', image_description, 
                       self.generate_image_callback)
  
  def generate_image_callback(self, result):
    """Callback for image generation"""
    if result["status"] == "success":
      # Image generated successfully
      if result.get("image_url"):
        # Set image from URL
        self.image_1.source = result["image_url"]
      elif result.get("image_data"):
        # Set image from data (if Anvil supports this)
        try:
          import base64
          from io import BytesIO
          img_data = base64.b64decode(result["image_data"])
          self.image_1.source = img_data  # This might need adjustment based on Anvil's API
        except:
          self.image_1.source = "https://via.placeholder.com/300x300.png?text=Image+Data+Error"
    else:
      # Image generation failed
      self.image_1.source = "https://via.placeholder.com/300x300.png?text=Image+Generation+Failed"
      print(f"Image generation error: {result.get('error')}")

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