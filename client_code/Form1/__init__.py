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
    self.check_table_btn = Button(text="Check/Create Table", icon="fa:table")
    self.check_table_btn.set_event_handler('click', self.check_create_table)

    self.init_memory_btn = Button(text="Initialize Memories", icon="fa:database")
    self.init_memory_btn.set_event_handler('click', self.initialize_memories)

    self.debug_memory_btn = Button(text="Debug Memories", icon="fa:bug")
    self.debug_memory_btn.set_event_handler('click', self.debug_memories)

    self.force_memory_btn = Button(text="Force Memory Inclusion", icon="fa:bolt")
    self.force_memory_btn.set_event_handler('click', self.force_memories)
  #  self.update_all_cards()

  def timer_1_tick(self, **event_args):
  #  self.update_all_cards()
    pass

  # def update_all_cards(self):
  #   try:
  #     # Mood + Thoughts always refresh
  #     self.label_mood.text = anvil.http.request(f'{API_BASE}/mood', json=True)['mood']
  #     thoughts = anvil.http.request(f'{API_BASE}/thoughts', json=True)['thoughts']
  #     self.text_area_thoughts.text = '\n'.join(thoughts)
  
  #     # Location check
  #     location_res = anvil.http.request(f'{API_BASE}/location', json=True)
  #     current_location = location_res['location']
  #     self.label_location.text = current_location
  
  #     if current_location != self._last_location:
  #       self._last_location = current_location
  #       image_res = anvil.http.request(f'{API_BASE}/location_image', json=True)
  #       self.image_location.source = image_res['url']
  #   except Exception as e:
  #     self.label_mood.text = f"Error: {e}"

  def button_send_click(self, **event_args):
      print("Button clicked")  # Confirm this actually fires
      user_msg = self.text_box_input.text
      self.text_area_chat.text += f"You: {user_msg}\n"
      self.text_box_input.text = ''

      try:
          res = anvil.server.call('chat_with_model', user_msg)
          self.text_area_chat.text += f"Nyx: {res['reply']}\n"
      except Exception as e:
          self.text_area_chat.text += f"Error: {e}\n"

  def text_box_input_pressed_enter(self, **event_args):
    """This method is called when the user presses Enter in this text box"""
    pass

  def check_create_table(self, **event_args):
 
      
  def initialize_memories(self, **event_args):
    """Initialize test memories"""
    result = anvil.server.call('initialize_memory_system')
    alert(f"Memory system: {result['status']}")
    
  def debug_memories(self, **event_args):
    """Print all stored memories"""
    from . import memory_testing
    result = anvil.server.call('print_all_memories')
    alert(f"Found {result['count']} memories. Check server logs for details.")
    
  def force_memories(self, **event_args):
    """Force memories to be included in next prompt"""
    from . import memory_testing
    result = anvil.server.call('force_memory_inclusion')
    if result['status'] == 'success':
      alert(f"Added {result['memories_included']} memories to system prompt")
    else:
      alert(f"Error: {result['message']}")

  def check_table_btn_click(self, **event_args):
   """Check if memories table exists and create it if not"""
    result = anvil.server.call('ensure_memories_table_exists')
    alert(f"Table status: {result['status']}")

  def init_memory_btn_click(self, **event_args):
    """This method is called when the button is clicked"""
    pass

  def debug_memory_btn_click(self, **event_args):
    """This method is called when the button is clicked"""
    pass

  def force_memory_btn_click(self, **event_args):
    """This method is called when the button is clicked"""
    pass

