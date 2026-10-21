"""Factory functions for the two kinds of client this project uses.

* get_openai_client()   -> OpenAI SDK, Azure OpenAI endpoint (plain model calls, Day 1)
* get_project_clients() -> Foundry SDK project client + its OpenAI client (agents, Days 2 and 3)

Both authenticate with Microsoft Entra ID (run `az login` first). No API keys.
"""
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import OpenAI

from . import config


def _credential() -> DefaultAzureCredential:
    # Same options the official Foundry IQ lab uses: skip credentials that are
    # not relevant on a developer machine so sign-in is fast and predictable.
    return DefaultAzureCredential(
        exclude_environment_credential=True,
        exclude_managed_identity_credential=True,
    )


def get_openai_client() -> OpenAI:
    """OpenAI SDK client for direct model calls (Responses API)."""
    config.require("AZURE_OPENAI_ENDPOINT")
    # TODO 1.1.b: Create a bearer token provider for "https://ai.azure.com/.default" and
    # return an OpenAI client that uses AZURE_OPENAI_ENDPOINT as base_url
    token_provider = get_bearer_token_provider(_credential(), "https://ai.azure.com/.default")
    return OpenAI(base_url=config.AZURE_OPENAI_ENDPOINT, api_key=token_provider)


def get_project_clients() -> tuple[AIProjectClient, OpenAI]:
    """Foundry project client and the OpenAI client that belongs to it."""
    config.require("PROJECT_ENDPOINT")
    # TODO 2.1.a: Create an AIProjectClient from PROJECT_ENDPOINT, then get its OpenAI client
    # with get_openai_client(); return both
    raise NotImplementedError("TODO 2.1.a")
