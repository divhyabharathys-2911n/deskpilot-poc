"""Synchronous wrapper around an MCP client session.

The MCP SDK is async, but Streamlit and our agent loop are synchronous. This class
runs the async session on a background thread and exposes plain blocking methods.

Two things it does on purpose:
  * It hides the `requester` argument from the model (see function_tools()).
  * It injects the signed-in user when a tool is called (see call()).
"""
import asyncio
import sys
import threading
from contextlib import AsyncExitStack

from azure.ai.projects.models import FunctionTool
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from .config import ROOT

HIDDEN_ARGS = {"requester"}  # arguments the app supplies, never the model


class TicketMCP:
    def __init__(self, env: dict | None = None) -> None:
        self._env = env  # extra environment variables for the server process (used by tests)
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._loop.run_forever, daemon=True)
        self._thread.start()
        self._stack = AsyncExitStack()
        self._session: ClientSession | None = None
        self.tools = []
        self._run(self._connect())

    def _run(self, coroutine, timeout: float = 60):
        return asyncio.run_coroutine_threadsafe(coroutine, self._loop).result(timeout)

    async def _connect(self) -> None:
        params = StdioServerParameters(
            command=sys.executable,
            args=[str(ROOT / "mcp_server" / "ticket_server.py")],
            env=self._env,
        )
        # TODO 2.3.e: Start the server process with stdio_client(params) and create a
        # ClientSession from its read and write streams. Enter both with
        # self._stack.enter_async_context(...), then await self._session.initialize()
        read, write = await self._stack.enter_async_context(stdio_client(params))
        self._session = await self._stack.enter_async_context(ClientSession(read, write))
        await self._session.initialize()
        # TODO 2.3.f: List the tools the server offers: store the result of await
        # self._session.list_tools() ".tools" in self.tools
        listing = await self._session.list_tools()
        self.tools = listing.tools

    def function_tools(self) -> list[FunctionTool]:
        """Turn each MCP tool into a FunctionTool for the agent, hiding `requester`."""
        tools = []
        for tool in self.tools:
            # TODO 2.3.g: Copy tool.input_schema, remove HIDDEN_ARGS from its "properties" and
            # "required" lists, then build FunctionTool(name=tool.name,
            # description=tool.description, parameters=schema, strict=False)
            schema = dict(tool.input_schema)
            schema["properties"] = {
                key: value for key, value in schema.get("properties", {}).items() if key not in HIDDEN_ARGS
            }
            schema["required"] = [key for key in schema.get("required", []) if key not in HIDDEN_ARGS]
            tools.append(
                FunctionTool(
                    name=tool.name,
                    description=tool.description or "",
                    parameters=schema,
                    strict=False,
                )
            )        
        return tools

    def has_tool(self, name: str) -> bool:
        return any(tool.name == name for tool in self.tools)

    def call(self, name: str, arguments: dict, requester: str) -> str:
        """Call an MCP tool as `requester` and return its text output."""
        # TODO 2.3.h: Build args = dict(arguments) with args["requester"] = requester (this
        # overrides anything the model sent), call the tool with await
        # self._session.call_tool(name, args) through self._run(...), and return the text of
        # the result content items joined with newlines
        args = dict(arguments)
        args["requester"] = requester
        result = self._run(self._session.call_tool(name, args))
        return "\n".join(item.text for item in result.content if getattr(item, "text", None))

    def close(self) -> None:
        try:
            self._run(self._stack.aclose(), timeout=10)
        except Exception:
            pass
        self._loop.call_soon_threadsafe(self._loop.stop)
