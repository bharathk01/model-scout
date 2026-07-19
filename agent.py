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

import sys
from pathlib import Path

from deepagents import create_deep_agent
from dotenv import load_dotenv

from model_provider import get_model
from tools import get_recent_models, get_trending_models, send_digest

load_dotenv()  # read provider settings from a local .env if present

SKILLS_DIR = str(Path(__file__).parent / "skills")

# A subagent runs in its own context window, so a long raw model list never
# pollutes the orchestrator's context — the orchestrator only sees the short,
# curated result the subagent hands back.
curator = {
    "name": "curator",
    "description": "Filters and ranks a raw Hugging Face model list into a short, notable shortlist with plain-language notes.",
    "system_prompt": (
        "You curate Hugging Face model listings. Given a raw list, drop noise "
        "(personal fine-tunes, zero-traction experiments) and return at most 5 "
        "notable models, each with one plain sentence on why it might matter. "
        "Be concise and never invent models that are not in the input."
    ),
}

agent = create_deep_agent(
    model=get_model(),  # provider chosen via MODEL_PROVIDER env var
    tools=[get_recent_models, get_trending_models, send_digest],
    system_prompt=(
        "You are ModelScout, an assistant that watches Hugging Face for model "
        "launches. At startup you only see skill names and descriptions. When a "
        "request matches a skill, read that skill's SKILL.md and follow its "
        "steps exactly, delegating to the 'curator' subagent where the skill "
        "says to. Do not improvise a workflow that a skill already defines."
    ),
    skills=[SKILLS_DIR],
    subagents=[curator],
)


def main() -> None:
    prompt = " ".join(sys.argv[1:]) or "Any new text-generation models in the last 24 hours?"
    result = agent.invoke({"messages": [{"role": "user", "content": prompt}]})
    print(result["messages"][-1].content)


if __name__ == "__main__":
    main()
