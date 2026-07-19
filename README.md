# ModelScout — a Hugging Face model-launch watcher (DeepAgents demo)

A small, working example of the "skills-as-workflows" pattern: an agent that
watches the Hugging Face Hub for newly launched (or trending) models and sends
you a short digest.

The point of the example: **the orchestrator holds no workflow logic.** It
wires in three tools, one subagent, and a `skills/` folder. Each `SKILL.md`
*is* a workflow. Adding a new kind of digest = adding a file, not editing
`agent.py`.

## Layout

```
model_scout/
├── agent.py                        # orchestrator: model + tools + skills + subagent
├── model_provider.py               # pick the LLM: Anthropic / Azure / Gemini / local
├── tools.py                        # real Hugging Face calls (no API key needed)
└── skills/
    ├── new-models-digest/SKILL.md  # workflow #1
    └── trending-weekly/SKILL.md    # workflow #2 — reuses the same tools + subagent
```

## Getting started

**Prerequisites:** Python 3.11+ and an API key for one model provider
(Anthropic, Azure OpenAI, or Google Gemini) — or a local OpenAI-compatible
server. The Hugging Face lookups themselves need no key.

**1. Get the code and enter the folder**

```bash
git clone <your-repo-url>
cd model_scout
```

**2. Create a Python environment and install dependencies**

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

**3. Configure your model (and, optionally, email)**

```bash
cp .env.example .env
```

Open `.env` and fill in one provider block. The simplest is Anthropic:

```
MODEL_PROVIDER=anthropic
MODEL_NAME=claude-sonnet-5
ANTHROPIC_API_KEY=sk-ant-...
```

(`.env` is gitignored, so your keys never get committed.)

**4. Run it**

```bash
python agent.py "any new text-to-image models in the last 12 hours?"
```

You'll get a digest printed to the terminal and saved under `./digests/`. If you
filled in the SMTP block in `.env`, it's emailed to you as well.

Try the other skill too:

```bash
python agent.py "what's trending on Hugging Face this week?"
```

### Switching model providers (just env vars)

| Provider | Env vars |
|----------|----------|
| Anthropic (Claude) | `MODEL_PROVIDER=anthropic` `ANTHROPIC_API_KEY=...` |
| Azure OpenAI | `MODEL_PROVIDER=azure` `MODEL_NAME=<deployment>` `AZURE_OPENAI_ENDPOINT=...` `OPENAI_API_VERSION=...` `AZURE_OPENAI_API_KEY=...` |
| Google Gemini | `MODEL_PROVIDER=gemini` `MODEL_NAME=gemini-2.0-flash` `GOOGLE_API_KEY=...` |
| Local (vLLM / Ollama / LM Studio / SGLang) | `MODEL_PROVIDER=local` `MODEL_NAME=<model>` `LOCAL_MODEL_BASE_URL=http://localhost:8000/v1` |

### Email notification (optional)

Set `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`, `EMAIL_FROM`, `EMAIL_TO` (and
optionally `SMTP_PORT`, default 587) and ModelScout emails each digest over
STARTTLS. If those aren't set, it just saves the digest to `./digests/`. For
Gmail, use an [App Password](https://support.google.com/accounts/answer/185833),
not your account password.

## Verified with

```
deepagents==0.6.12
langchain==1.3.14
langchain-anthropic==1.4.8
langchain-openai==1.3.5
langchain-google-genai==4.2.7
langgraph==1.2.9
huggingface_hub==1.24.0
```

The Hugging Face tool calls and the agent build (skill discovery + all four
model providers) were run and confirmed working. The full LLM turn needs your
own API key / endpoint.
