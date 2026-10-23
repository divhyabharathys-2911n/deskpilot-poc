"""Run one turn of a Foundry agent, including tool calls.

Every agent in DeskPilot is called the same way (the Responses API with an `agent_reference`),
so the loop lives here once:

  1. add the user's message to the agent's conversation
  2. ask for a response from the agent
  3. if the agent wants approval (knowledge base tool) -> approve and ask again
  4. if the agent calls one of OUR functions           -> run it, send the output, ask again
  5. collect the final text, citations and any files the code interpreter produced
"""
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from common import config


@dataclass
class TurnResult:
    text: str = ""
    tools: list = field(default_factory=list)       # trace of tool activity
    citations: list = field(default_factory=list)   # sources the answer used
    files: list = field(default_factory=list)       # local paths of generated files (charts)


def agent_ref(agent_name: str) -> dict:
    return {"agent_reference": {"name": agent_name, "type": "agent_reference"}}


def _short(value, limit: int = 400) -> str:
    text = value if isinstance(value, str) else str(value)
    return text if len(text) <= limit else text[:limit] + " ..."


def _trace_other_items(result: TurnResult, output_items) -> None:
    """Record tool activity that happens inside the service (code interpreter, search)."""
    for item in output_items:
        kind = getattr(item, "type", "")
        if kind == "code_interpreter_call":
            result.tools.append({"type": "code_interpreter", "name": "code_interpreter",
                                 "detail": _short(getattr(item, "code", "") or "")})
        elif kind in ("file_search_call", "web_search_call", "mcp_call"):
            result.tools.append({"type": kind, "name": getattr(item, "name", kind),
                                 "detail": _short(getattr(item, "arguments", "") or "")})


def _save_container_file(openai_client, annotation) -> Path:
    """Download a file made by the code interpreter (for example a chart) to agent_outputs/."""
    config.OUTPUT_DIR.mkdir(exist_ok=True)
    content = openai_client.containers.files.content.retrieve(
        file_id=annotation.file_id, container_id=annotation.container_id
    )
    name = Path(getattr(annotation, "filename", None) or f"{annotation.file_id}.bin").name
    path = config.OUTPUT_DIR / f"{int(time.time())}_{name}"
    path.write_bytes(content.read())
    return path


def _collect_text_and_sources(openai_client, response, result: TurnResult) -> None:
    result.text = response.output_text or ""
    seen = set()
    for item in response.output:
        if getattr(item, "type", "") != "message":
            continue
        for content in getattr(item, "content", None) or []:
            for annotation in getattr(content, "annotations", None) or []:
                kind = getattr(annotation, "type", "")
                if kind == "container_file_citation":
                    path = _save_container_file(openai_client, annotation)
                    if path not in result.files:
                        result.files.append(path)
                    continue
                title = getattr(annotation, "title", None) or getattr(annotation, "filename", None)
                url = getattr(annotation, "url", None)
                if (title or url) and (title, url) not in seen:
                    seen.add((title, url))
                    result.citations.append({"type": kind, "title": title, "url": url})


def run_agent_turn(openai_client, agent_name: str, conversation_id: str, user_text: str,
                   function_handler: Callable[[str, str], str] | None = None,
                   max_rounds: int = 8) -> TurnResult:
    """Send `user_text` to the agent and return its final answer plus a trace.

    function_handler(name, arguments_json) -> output string. Pass it for agents that have
    function tools; leave it None for agents without them.
    """
    result = TurnResult()

    # TODO 2.1.b: Add the user message to the conversation:
    # openai_client.conversations.items.create(conversation_id=conversation_id,
    # items=[{"type": "message", "role": "user", "content": user_text}])
    openai_client.conversations.items.create(
        conversation_id=conversation_id,
        items=[{"type": "message", "role": "user", "content": user_text}],
    )
    # TODO 2.1.c: Ask the agent for a response:
    # openai_client.responses.create(conversation=conversation_id,
    # extra_body=agent_ref(agent_name), input="")
    response = openai_client.responses.create(
        conversation=conversation_id, extra_body=agent_ref(agent_name), input=""
    )

    for _ in range(max_rounds):
        _trace_other_items(result, response.output)
        approvals = [i for i in response.output if getattr(i, "type", "") == "mcp_approval_request"]
        calls = [i for i in response.output if getattr(i, "type", "") == "function_call"]

        if approvals:
            # TODO 2.1.d: For each approval request build {"type": "mcp_approval_response",
            # "approval_request_id": request.id, "approve": True} and add them with
            # openai_client.conversations.items.create(...); also append a trace entry. Then
            # get the next response with openai_client.responses.create(conversation=...,
            # extra_body=agent_ref(agent_name), input="") and continue the loop
            decisions = []
            for request in approvals:
                result.tools.append({"type": "knowledge_base", "name": request.name,
                                    "detail": _short(request.arguments)})
            decisions.append({"type": "mcp_approval_response",
                            "approval_request_id": request.id, "approve": True})
            openai_client.conversations.items.create(conversation_id=conversation_id, items=decisions)
            response = openai_client.responses.create(
                conversation=conversation_id, extra_body=agent_ref(agent_name), input=""
            )
            continue

        if calls and function_handler is not None:
            # TODO 2.2.f: For each function_call run function_handler(call.name,
            # call.arguments) and build {"type": "function_call_output", "call_id":
            # call.call_id, "output": output}; add a trace entry with name, arguments and a
            # short result. Then call
            # openai_client.responses.create(conversation=conversation_id, input=outputs,
            # extra_body=agent_ref(agent_name)) and continue the loop. Use the conversation
            # (not previous_response_id) so the next message does not fail with "No tool
            # output found"
            raise NotImplementedError("TODO 2.2.f")

        break

    if getattr(response, "status", "") == "failed":
        raise RuntimeError(f"The agent run failed: {getattr(response, 'error', 'unknown error')}")
    _collect_text_and_sources(openai_client, response, result)
    return result
