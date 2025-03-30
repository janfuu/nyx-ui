import jinja2
import os

# Load the template from file or inline (can also load from Anvil asset if needed)
PROMPT_TEMPLATE = """
<bos>
{%- if messages and messages[0]['role'] == 'system' -%}
  {{ messages[0]['content'] | trim + '\n\n' }}
  {%- set loop_messages = messages[1:] -%}
{%- else -%}
  {%- set loop_messages = messages -%}
{%- endif %}

{%- for message in loop_messages %}
  {%- set role = message['role'] %}
  {%- if role == 'assistant' %}
    {%- set role = 'model' %}
  {%- endif %}
  <start_of_turn>{{ role }}
{{ message['content'] | trim }}
<end_of_turn>
{%- endfor %}

<start_of_turn>model
"""

jinja_env = jinja2.Environment(
    loader=jinja2.BaseLoader(),
    trim_blocks=True,
    lstrip_blocks=True
)

template = jinja_env.from_string(PROMPT_TEMPLATE)

def build_prompt(messages):
    return template.render(messages=messages)
