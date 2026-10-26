"""Step 1.3 (second part): the same chat app, with ONE function tool the model can call.

This is a tool call made directly on a model. Compare it with the agent you build on Day 2:
here YOUR code runs the loop (detect call, run function, send result back).
Run:  python 02_chat_baseline/chat_tool.py --user aarav.shah
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common import config, db
from common.clients import get_openai_client

INSTRUCTIONS = (
    "You are DeskPilot, an IT help desk assistant. Use the lookup_ticket tool when the user asks "
    "about the status of a ticket. Keep answers short."
)

# TODO 1.3.c: Define TOOLS: a list with one function tool dict {"type": "function", "name":
# "lookup_ticket", "description": ..., "parameters": {JSON schema with one required string
# "ticket_id"}, "strict": True} (additionalProperties must be False)
TOOLS = [
    {
        "type": "function",
        "name": "lookup_ticket",
        "description": "Look up the status and details of a support ticket by its ID, for example INC-1001.",
        "parameters": {
            "type": "object",
            "properties": {"ticket_id": {"type": "string", "description": "Ticket ID such as INC-1001."}},
            "required": ["ticket_id"],
            "additionalProperties": False,
        },
        "strict": True,
    }
]

def lookup_ticket(user: str, ticket_id: str) -> str:
    try:
        return json.dumps(db.get_ticket(user, ticket_id))
    except (ValueError, db.PermissionDenied) as ex:
        return json.dumps({"error": str(ex)})


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--user", default="aarav.shah", choices=list(config.USERS))
    args = parser.parse_args()
    config.require("AZURE_OPENAI_ENDPOINT", "MODEL_DEPLOYMENT")
    db.init_db()
    client = get_openai_client()
    last_response_id = None
    print(f"Signed in as {args.user}. Try: What is the status of INC-1001? Type 'quit' to exit.")
    while True:
        text = input("\nYou: ").strip()
        if text.lower() == "quit":
            break
        if not text:
            continue
        response = client.responses.create(
            model=config.MODEL_DEPLOYMENT, instructions=INSTRUCTIONS, input=text,
            previous_response_id=last_response_id, tools=TOOLS,
        )
        # TODO 1.3.d: Loop while the response contains items of type "function_call": for each
        # one, run lookup_ticket(args.user, ticket_id from json.loads(item.arguments)) and
        # collect {"type": "function_call_output", "call_id": item.call_id, "output": result}.
        # Then call client.responses.create again with input=those outputs,
        # previous_response_id=response.id, and the same model, instructions and tools
        while True:
            calls = [item for item in response.output if item.type == "function_call"]
            if not calls:
                break
            outputs = []
            for call in calls:
                arguments = json.loads(call.arguments)
                print(f" [tool call] {call.name}({arguments})")
                outputs.append({
                    "type": "function_call_output",
                    "call_id": call.call_id,
                    "output": lookup_ticket(args.user, arguments["ticket_id"]),
                })
            response = client.responses.create(
                model=config.MODEL_DEPLOYMENT, instructions=INSTRUCTIONS, input=outputs,
                previous_response_id=response.id, tools=TOOLS,
            )
        print("DeskPilot:", response.output_text)
        last_response_id = response.id


if __name__ == "__main__":
    main()
