"""Knowledge agent wrapper.

The agent itself is created in the Foundry portal (step 2.1): it is connected to a Foundry IQ
knowledge base built on Azure Blob Storage + Azure AI Search. This class only calls it.
"""
from common import config
from .runtime import TurnResult, run_agent_turn


class KnowledgeAgent:
    def __init__(self, project_client, openai_client) -> None:
        self.openai_client = openai_client
        self.name = config.KNOWLEDGE_AGENT_NAME
        # TODO 2.1.e: Load the agent you created in the portal with
        # project_client.agents.get(agent_name=self.name) and keep it in self.agent. This
        # fails early with a clear error if the name in .env is wrong
        self.agent = project_client.agents.get(agent_name=self.name)

    def new_conversation(self) -> str:
        return self.openai_client.conversations.create(items=[]).id

    def ask(self, conversation_id: str, text: str) -> TurnResult:
        return run_agent_turn(self.openai_client, self.name, conversation_id, text)
