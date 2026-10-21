"""Step 1.1 check: can this machine reach your Foundry project and model?

Run:  python scripts/check_connection.py
"""
import sys
from pathlib import Path
from urllib import response

from openai import OpenAI

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common import config
from common.clients import get_openai_client


def main() -> None:
    config.require("AZURE_OPENAI_ENDPOINT", "MODEL_DEPLOYMENT")
    client = get_openai_client()
    # TODO 1.1.a: Call client.responses.create(model=config.MODEL_DEPLOYMENT, input="Reply
    # with the single word: ready") and print response.output_text
    response = client.responses.create(
        model=config.MODEL_DEPLOYMENT,
        input="Reply with the single word: ready",
    )
    print("Model replied:", response.output_text)
    print("Connection OK.")


if __name__ == "__main__":
    main()
