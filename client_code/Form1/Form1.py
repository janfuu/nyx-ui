from ._anvil_designer import Form1Template
from anvil import *
import anvil.server
import anvil.http

class Form1(Form1Template):

  def __init__(self, **properties):
    self.init_components(**properties)
    self.timer_1.interval = 3
    self.update_all_cards()

  def timer_1_tick(self, **event_args):
    self.update_all_cards()

  def update_all_cards(self):
    try:
      self.label_mood.text = anvil.http.request('http://localhost:8000/api/mood', json=True)['mood']
      self.image_1.source = anvil.http.request('http://localhost:8000/api/image', json=True)['url']
      self.label_location.text = anvil.http.request('http://localhost:8000/api/location', json=True)['location']
      thoughts = anvil.http.request('http://localhost:8000/api/thoughts', json=True)['thoughts']
      self.text_area_thoughts.text = '\n'.join(thoughts)
    except Exception as e:
      self.label_mood.text = f"Error: {e}"

  def button_send_click(self, **event_args):
    user_msg = self.text_box_input.text
    self.text_area_chat.text += f'You: {user_msg}\n'
    self.text_box_input.text = ''
    try:
      res = anvil.http.request(
        'http://localhost:8000/api/chat',
        method='POST',
        json={'message': user_msg}
      )
      self.text_area_chat.text += f'Nyx: {res["reply"]}\n'
    except Exception as e:
      self.text_area_chat.text += f'Error: {e}\n'
