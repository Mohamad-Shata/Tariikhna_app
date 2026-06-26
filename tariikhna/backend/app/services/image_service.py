"""
Calls fal.ai's Flux.1 dev model using the image_prompt field from your
fine-tuned LLM's schema output. This is the "bridge" between text and image:
the LLM never talks to fal.ai directly, this service is the only place that does.
"""
import os
import fal_client
from app.config import settings

# fal_client reads the FAL_KEY environment variable directly — it does not
# accept the key as a module attribute, so we set the env var explicitly
# here in case .env loading order means it wasn't already present.
if settings.fal_key:
    os.environ["FAL_KEY"] = settings.fal_key


def generate_image(image_prompt: str, image_size: str = "square_hd") -> str:
    """
    image_prompt: the 250-300 word prompt string from the scene schema
    returns: URL of the generated image
    """
    if not settings.fal_key:
        raise RuntimeError("FAL_KEY is not set in .env")

    result = fal_client.run(
        "fal-ai/flux/dev",
        arguments={
            "prompt": image_prompt,
            "image_size": image_size,
            "num_inference_steps": 28,
            "guidance_scale": 3.5,
        },
    )
    # fal_client returns a dict with an "images" list; we use the first one
    return result["images"][0]["url"]