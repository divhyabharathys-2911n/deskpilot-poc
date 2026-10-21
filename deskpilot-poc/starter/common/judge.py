"""LLM-as-judge helper used by the model comparison, the red-team script and the evaluation."""
import json
import re

from . import config


def judge_json(openai_client, instructions: str, prompt: str, model: str | None = None) -> dict:
    """Ask a model to grade something and return its answer as a dict.

    The instructions must tell the judge to reply with a single JSON object.
    Returns {"error": "..."} if the reply cannot be parsed.
    """
    response = openai_client.responses.create(
        model=model or config.MODEL_DEPLOYMENT,
        instructions=instructions,
        input=prompt,
    )
    text = (response.output_text or "").strip()
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return {"error": f"Judge reply was not JSON: {text[:200]}"}
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError as ex:
        return {"error": f"Judge JSON could not be parsed: {ex}"}
