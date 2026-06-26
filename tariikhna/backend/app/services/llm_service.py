"""
Calls your fine-tuned Llama-3.1-8B model to turn a narrative unit into a
full scene schema (matching your training data's target JSON, including
the image_prompt field that feeds the image service).

Two modes, controlled by LLM_MODE in .env:
  - "remote": POSTs to an HTTP endpoint you're hosting elsewhere (e.g. a
    Colab/Kaggle notebook with a GPU, exposed via ngrok). Use this if your
    FastAPI machine has no GPU. <-- recommended for most laptops
  - "local": loads the model directly in this process with Unsloth/PEFT.
    Only works if the machine running FastAPI has a CUDA GPU.
"""
import json
import re
import httpx
from app.config import settings

SYSTEM_PROMPT = (
    "You are a specialist in creating children's Islamic educational comics "
    "(ages 6-12) for the Tariikhna platform. Convert ONE visual scene into a "
    "complete schema with a DETAILED image generation prompt. Follow Islamic "
    "depiction rules: prophets never shown by face (refer to them by clothing/"
    "position only), women always fully and modestly dressed. Output only JSON."
)

_local_model = None
_local_tokenizer = None


def _load_local_model():
    """Lazily loads the model into GPU memory on first use (local mode only)."""
    global _local_model, _local_tokenizer
    if _local_model is not None:
        return
    from unsloth import FastLanguageModel

    _local_model, _local_tokenizer = FastLanguageModel.from_pretrained(
        model_name=settings.hf_model_repo,
        max_seq_length=4096,
        load_in_4bit=True,
        token=settings.hf_token or None,
    )
    FastLanguageModel.for_inference(_local_model)


def _extract_json(raw_text: str) -> dict:
    """The model sometimes wraps JSON in prose or code fences — pull out the
    first {...} block and parse it."""
    match = re.search(r"\{.*\}", raw_text, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object found in model output: {raw_text[:200]}")
    return json.loads(match.group(0))


def generate_scene_schema(narrative_unit: dict) -> dict:
    """
    narrative_unit: dict matching NarrativeUnitInput fields
    returns: parsed schema dict (matching SceneSchemaOutput)
    """
    user_prompt = f"Generate the schema for this scene:\n\n{json.dumps(narrative_unit, ensure_ascii=False)}"

    if settings.llm_mode == "remote":
        return _generate_remote(user_prompt)
    return _generate_local(user_prompt)


def _generate_remote(user_prompt: str) -> dict:
    if not settings.llm_remote_url:
        raise RuntimeError("LLM_MODE=remote but LLM_REMOTE_URL is not set in .env")

    response = httpx.post(
        settings.llm_remote_url,
        json={"system_prompt": SYSTEM_PROMPT, "user_prompt": user_prompt},
        timeout=120.0,
    )
    response.raise_for_status()
    raw_text = response.json()["text"]
    return _extract_json(raw_text)


def _generate_local(user_prompt: str) -> dict:
    _load_local_model()
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]
    inputs = _local_tokenizer.apply_chat_template(
        messages, tokenize=True, add_generation_prompt=True, return_tensors="pt"
    ).to("cuda")

    outputs = _local_model.generate(
        input_ids=inputs, max_new_tokens=1024, temperature=0.6, use_cache=True
    )
    full_text = _local_tokenizer.batch_decode(outputs)[0]
    generated_part = full_text.split("assistant")[-1]
    return _extract_json(generated_part)