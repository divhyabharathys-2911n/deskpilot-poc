"""Central configuration. Every other module imports its settings from here."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

# --- Azure / Foundry settings (set in .env) ---------------------------------
# Project endpoint: used by the Foundry SDK (agents). Example:
#   https://<resource>.services.ai.azure.com/api/projects/<project>
PROJECT_ENDPOINT = os.getenv("PROJECT_ENDPOINT", "")
# Azure OpenAI endpoint: used by the OpenAI SDK for plain model calls (Day 1).
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "")
# Deployment name of the chat model you chose in step 1.2.
MODEL_DEPLOYMENT = os.getenv("MODEL_DEPLOYMENT", "gpt-5")
# Comma-separated deployments to compare in step 1.2 (defaults to the main one).
MODEL_DEPLOYMENTS = [
    m.strip() for m in os.getenv("MODEL_DEPLOYMENTS", MODEL_DEPLOYMENT).split(",") if m.strip()
]
# Agent names (the knowledge agent is created in the portal, the others by code).
KNOWLEDGE_AGENT_NAME = os.getenv("KNOWLEDGE_AGENT_NAME", "deskpilot-knowledge")
TICKET_AGENT_NAME = os.getenv("TICKET_AGENT_NAME", "deskpilot-ticket")
TRIAGE_AGENT_NAME = os.getenv("TRIAGE_AGENT_NAME", "deskpilot-triage")
# Optional: name of the custom guardrail (RAI policy) from step 1.4.
RAI_POLICY_NAME = os.getenv("RAI_POLICY_NAME", "")

# --- Local paths --------------------------------------------------------------
DATA_DIR = ROOT / "data"
DB_PATH = Path(os.getenv("DESKPILOT_DB", str(DATA_DIR / "tickets.db")))  # override is used by the tests
SEED_CSV = DATA_DIR / "seed_tickets.csv"
KB_DIR = DATA_DIR / "kb"
KB_SRC_DIR = DATA_DIR / "kb_src"
OUTPUT_DIR = ROOT / "agent_outputs"

# --- Help desk reference data -------------------------------------------------
# Dummy users. Roles are enforced in code (common/db.py), not only in prompts.
USERS = {
    "aarav.shah": {"name": "Aarav Shah", "role": "employee"},
    "diya.patel": {"name": "Diya Patel", "role": "employee"},
    "kabir.mehta": {"name": "Kabir Mehta", "role": "employee"},
    "meera.iyer": {"name": "Meera Iyer", "role": "employee"},
    "rohan.das": {"name": "Rohan Das", "role": "employee"},
    "it.admin": {"name": "IT Admin", "role": "admin"},
}
CATEGORIES = [
    "VPN", "Password", "MFA", "Printer", "Email",
    "WiFi", "Software", "Laptop", "Access", "Security",
]
PRIORITIES = ["Low", "Medium", "High", "Critical"]
STATUSES = ["Open", "In Progress", "Resolved", "Closed"]


def require(*names: str) -> None:
    """Stop early with a clear message when a required setting is missing."""
    missing = [n for n in names if not globals().get(n)]
    if missing:
        raise RuntimeError(
            "Missing settings in .env: " + ", ".join(missing)
            + ". Copy .env.example to .env and fill in the values."
        )
