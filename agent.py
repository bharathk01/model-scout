"""ModelScout — a Hugging Face model-launch watcher built with DeepAgents.

The idea this example demonstrates: the orchestrator holds NO workflow logic.
It gets three things wired in —

    1. tools     : plain functions the agent can call (the Hugging Face calls)
    2. subagents : helpers that run in their own context window
    3. skills    : a folder of SKILL.md files, each of which *is* a workflow

Adding a new kind of digest means adding a SKILL.md file to ./skills. It does
NOT mean editing this file. That's the whole point.

The model is chosen by `get_model()` (see model_provider.py), so the same agent
runs on Claude, Azure OpenAI, Gemini, or any local OpenAI-compatible server
just by changing an env var.

Run:
    export MODEL_PROVIDER=anthropic ANTHROPIC_API_KEY=...
    python agent.py "any new text-to-image models in the last 12 hours?"
"""

import logging
import sys
from pathlib import Path

from deepagents import create_deep_agent
from dotenv import load_dotenv

from logging_config import configure_logging
from model_provider import get_model
from prompts import CURATOR_PROMPT, SYSTEM_PROMPT
from tools import get_recent_models, get_trending_models, send_digest

load_dotenv()  # read provider settings from a local .env if present
configure_logging()
logger = logging.getLogger("modelscout.agent")

SKILLS_DIR = str(Path(__file__).parent / "skills")

# A subagent runs in its own context window, so a long raw model list never
# pollutes the orchestrator's context — the orchestrator only sees the short,
# curated result the subagent hands back.
curator = {
    "name": "curator",
    "description": (
        "Curates raw Hugging Face model listings into a concise, "
        "high-signal shortlist."
    ),
    "system_prompt": CURATOR_PROMPT,
}


def build_agent():
    """Create and configure the ModelScout DeepAgent."""

    model = get_model()
    logger.info("Building ModelScout agent with model=%s", type(model).__name__)
    return create_deep_agent(
        model=model,
        tools=[get_recent_models, get_trending_models, send_digest],
        system_prompt=SYSTEM_PROMPT,
        skills=[SKILLS_DIR],
        subagents=[curator],
    )


agent = build_agent()


def main() -> None:
    prompt = " ".join(sys.argv[1:]) or "Any new text-generation models in the last 24 hours?"
    logger.info("Running agent, prompt=%r", prompt)
    result = agent.invoke({"messages": [{"role": "user", "content": prompt}]})
    print(result["messages"][-1].content)


if __name__ == "__main__":
    main()
