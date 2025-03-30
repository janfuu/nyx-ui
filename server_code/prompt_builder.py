# prompt_builder.py
import jinja2
import os

# Enhanced template that handles memory inclusion
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
    """
    Build prompt from messages with enhanced memory handling.
    The system message should already have memories incorporated.
    """
    return template.render(messages=messages)


# Alternative: Memory-focused prompt template
MEMORY_PROMPT_TEMPLATE = """
<bos>
{%- if messages and messages[0]['role'] == 'system' -%}
  {{ messages[0]['content'] | trim }}
  {%- set loop_messages = messages[1:] -%}
{%- else -%}
  {%- set loop_messages = messages -%}
{%- endif %}

{%- if memories %}
IMPORTANT MEMORIES ABOUT THE USER:
{% for memory in memories %}
- {{ memory.type | upper }}: {{ memory.value }}
{%- endfor %}
{% endif %}

CONVERSATION HISTORY:
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

memory_template = jinja_env.from_string(MEMORY_PROMPT_TEMPLATE)

def build_memory_prompt(messages, memories=None):
    """
    Alternative prompt builder that explicitly formats memories
    in their own section rather than incorporating them into
    the system message.
    """
    return memory_template.render(messages=messages, memories=memories or [])