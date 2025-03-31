# image_generation.py
import anvil.server
import asyncio
import os
from runware import Runware, IImageInference, IPromptEnhance

RUNWARE_API_KEY = os.environ.get("RUNWARE_API_KEY")

def run_async(coro):
    return asyncio.new_event_loop().run_until_complete(coro)

@anvil.server.background_task
def generate_image_task(prompt, width=512, height=512, model="civitai:101055@128078"):
    anvil.server.task_state['status'] = 'starting'

    try:
        runware = Runware(api_key=RUNWARE_API_KEY)
        run_async(runware.connect())

        # Prompt enhancement
        enhancer = IPromptEnhance(prompt=prompt, promptVersions=1, promptMaxLength=77)
        anvil.server.task_state['status'] = 'enhancing'

        enhanced_list = run_async(runware.promptEnhance(promptEnhancer=enhancer))
        enhanced_prompt = enhanced_list[0].text

        # Generate image
        request = IImageInference(
            positivePrompt=enhanced_prompt,
            model=model,
            numberResults=1,
            negativePrompt="blurry, distorted",
            height=height,
            width=width,
        )
        anvil.server.task_state['status'] = 'generating'

        result = run_async(runware.imageInference(requestImage=request))
        if not result or not result[0].imageURL:
            raise Exception("No image URL returned")

        anvil.server.task_state['status'] = 'complete'
        return {
            "status": "success",
            "image_url": result[0].imageURL,
            "enhanced_prompt": enhanced_prompt
        }

    except Exception as e:
        anvil.server.task_state['status'] = 'error'
        anvil.server.task_state['error'] = str(e)
        raise

@anvil.server.callable
def launch_image_task(prompt):
    task = anvil.server.launch_background_task('generate_image_task', prompt)
    return task.get_id()  # return the ID for tracking later

@anvil.server.callable
def check_image_task(task_id):
    task = anvil.server.get_background_task(task_id)
    state = task.get_state()
    result = {
        "status": state.get("status"),
        "error": state.get("error"),
        "is_running": task.is_running(),
        "is_completed": task.is_completed(),
        "termination": task.get_termination_status()
    }

    if task.is_completed():
        result["result"] = task.get_return_value()

    return result
