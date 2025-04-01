# image_generation.py

import anvil.server
import asyncio
import os
from runware import Runware, IImageInference, IPromptEnhance

RUNWARE_API_KEY = os.environ.get("RUNWARE_API_KEY")

NYX_DESCRIPTION = (
    "a futuristic woman with shimmering skin and chrome facial accents, "
    "dark hair, "
)


def references_nyx(prompt: str) -> bool:
    terms = ["me", "my", "myself", "i "]
    prompt_lower = prompt.lower()
    return any(term in prompt_lower for term in terms)


@anvil.server.background_task
def generate_image_task(prompt):
    """Background task to enhance a prompt and generate an image using Runware."""
    anvil.server.task_state['status'] = 'starting'

    def set_state(stage, msg=None):
        anvil.server.task_state['status'] = stage
        if msg:
            anvil.server.task_state['log'] = msg

    async def wrapped():
        try:
            set_state('connecting')
            runware = Runware(api_key=RUNWARE_API_KEY)
            await runware.connect()

            set_state('enhancing')
            # Add reference to her appearance
            if references_nyx(prompt):
                print("[Nyx] Self-reference detected — injecting visual description.")
                prompt = f"{NYX_DESCRIPTION}, {prompt}"

            enhancer = IPromptEnhance(prompt=prompt, promptVersions=1, promptMaxLength=77)
            enhanced = await runware.promptEnhance(promptEnhancer=enhancer)
            enhanced_prompt = enhanced[0].text

            set_state('generating', enhanced_prompt)
            request = IImageInference(
                positivePrompt=enhanced_prompt,
                model="civitai:101055@128078",
                numberResults=1,
                negativePrompt="blurry, distorted",
                height=512,
                width=512,
            )

            result = await runware.imageInference(requestImage=request)
            if result and result[0].imageURL:
                set_state('complete')
                return {
                    "status": "success",
                    "image_url": result[0].imageURL,
                    "enhanced_prompt": enhanced_prompt
                }

            set_state('error', "No image returned")
            return {"status": "error", "error": "No image returned"}

        except Exception as e:
            set_state('error', str(e))
            return {"status": "error", "error": str(e)}

    return asyncio.run(wrapped())


@anvil.server.callable
def launch_image_task(prompt):
    """Launch a background task to generate an image."""
    task = anvil.server.launch_background_task('generate_image_task', prompt)
    return task.get_id()


@anvil.server.callable
def check_image_task(task_id):
    """Check the status and result of a previously launched image task."""
    task = anvil.server.get_background_task(task_id)
    state = task.get_state()

    result = {
        "status": state.get("status"),
        "log": state.get("log"),
        "error": state.get("error"),
        "is_running": task.is_running(),
        "is_completed": task.is_completed(),
        "termination": task.get_termination_status()
    }

    if task.is_completed():
        result["result"] = task.get_return_value()

    return result
