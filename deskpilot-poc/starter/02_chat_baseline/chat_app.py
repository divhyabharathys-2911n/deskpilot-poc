"""Step 1.3: baseline help desk chat app (no agents, no knowledge base).

Uses the OpenAI SDK and the Responses API, with conversation tracking and streaming.
Run:  python 02_chat_baseline/chat_app.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common import config
from common.clients import get_openai_client

INSTRUCTIONS = (
    "You are DeskPilot, an IT help desk assistant. Give short, practical answers. "
    "If you do not know a company-specific fact, say so instead of guessing."
)


def main() -> None:
    config.require("AZURE_OPENAI_ENDPOINT", "MODEL_DEPLOYMENT")
    client = get_openai_client()
    last_response_id = None
    print("DeskPilot baseline chat. Type 'quit' to exit.")
    while True:
        text = input("\nYou: ").strip()
        if text.lower() == "quit":
            break
        if not text:
            continue
        # TODO 1.3.a: Call client.responses.create(...) with model, instructions, input,
        # previous_response_id=last_response_id and stream=True. Print each
        # "response.output_text.delta" event's delta (end=""), and save event.response.id into
        # last_response_id on the "response.completed" event
        raise NotImplementedError("TODO 1.3.a")


if __name__ == "__main__":
    main()
