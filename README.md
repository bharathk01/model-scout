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
model-scout/
├── agent.py                        # orchestrator: model + tools + skills + subagent
├── app.py                          # FastAPI wrapper — runs the same agent over HTTP
├── chat_cli.py                     # terminal chat UI, talks to the FastAPI app
├── logging_config.py               # shared logging setup (console + logs/modelscout.log)
├── model_provider.py               # pick the LLM: Anthropic / Azure / Gemini / local
├── prompts.py                      # system + curator subagent prompts
├── tools.py                        # real Hugging Face calls (no API key needed)
├── SMTP_SETUP.md                   # optional email configuration guide
└── skills/
    ├── discover-models/SKILL.md          # workflow #1
    └── discover-trending-models/SKILL.md # workflow #2 — reuses the same tools + subagent
```

## Getting started

**Prerequisites:** Python 3.11+ and an API key for one model provider
(Anthropic, Azure OpenAI, or Google Gemini) — or a local OpenAI-compatible
server. The Hugging Face lookups themselves need no key.

**1. Get the code and enter the folder**

```bash
git clone <your-repo-url>
cd model-scout
```

**2. Create a Python environment and install dependencies**

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

**3. Configure your model (and, optionally, email)**

```bash
copy .env.example .env
```

Open `.env` and fill in one provider block. For your local setup, use:

```ini
MODEL_PROVIDER=local
MODEL_NAME=qwen3-4b-instruct
LOCAL_MODEL_BASE_URL=http://127.0.0.1:1234/v1
LOCAL_MODEL_API_KEY=not-needed
```

(`.env` is gitignored, so your keys never get committed.)

**4. Run the agent from the terminal**

```bash
python agent.py "any new text-to-image models in the last 12 hours?"
```

You should see a digest printed to the terminal and saved under `./digests/`.

Try the other skill too:

```bash
python agent.py "what's trending on Hugging Face this week?"
```

**5. Run the FastAPI app**

`app.py` is a thin HTTP wrapper around the *same* agent from step 4 — every
request runs the full skill + tools + curator workflow, not a raw chat call.

Start the API server:

```bash
python app.py
```

Then in another terminal, call it:

```bash
curl http://127.0.0.1:8015/health
```

```bash
curl -X POST http://127.0.0.1:8015/ask -H "Content-Type: application/json" -d "{\"prompt\":\"any new text-to-image models in the last 12 hours?\"}"
```

### Switching model providers (just env vars)

| Provider | Env vars |
|----------|----------|
| Anthropic (Claude) | `MODEL_PROVIDER=anthropic` `ANTHROPIC_API_KEY=...` |
| Azure OpenAI | `MODEL_PROVIDER=azure` `MODEL_NAME=<deployment>` `AZURE_OPENAI_ENDPOINT=...` `OPENAI_API_VERSION=...` `AZURE_OPENAI_API_KEY=...` |
| Google Gemini | `MODEL_PROVIDER=gemini` `MODEL_NAME=gemini-3.1-flash-lite` `GOOGLE_API_KEY=...` |
| Local (vLLM / Ollama / LM Studio / SGLang) | `MODEL_PROVIDER=local` `MODEL_NAME=<model>` `LOCAL_MODEL_BASE_URL=http://localhost:8000/v1` |

Notes:
- The full agent prompt (system prompt + skills + tool schemas) is a few
  thousand tokens before the conversation even starts. Small local models with
  a short context window (e.g. a 4B model capped at ~6K tokens) can overflow
  on this — widen the context window in your local server, or use a hosted
  provider for anything beyond quick local smoke-testing.
- A single request can trigger 5-10+ model calls (skill matching, tool calls,
  the curator subagent), so on Gemini's free tier, pin `MODEL_NAME` to a
  specific stable model rather than a `-latest` alias — those can silently
  resolve to a brand-new preview model with a much stricter introductory
  quota (as low as 5 requests/minute), which the agent will blow through
  immediately.

### Email notification (optional)

Set `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`, `EMAIL_FROM`, `EMAIL_TO` (and
optionally `SMTP_PORT`, default 587). The agent's `send_digest` tool then
emails each digest it produces automatically. If those values are missing,
it just saves the digest to `./digests/`.

For Gmail, use an [App Password](https://support.google.com/accounts/answer/185833),
not your account password. For detailed setup steps, see [SMTP_SETUP.md](SMTP_SETUP.md).
Example values:

```ini
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
EMAIL_FROM=your-email@gmail.com
EMAIL_TO=recipient@example.com
```

Example request that triggers a digest (and, with SMTP configured, an email):

```bash
curl -X POST http://127.0.0.1:8015/ask -H "Content-Type: application/json" -d '{"prompt":"any new text-generation models today?"}'
```

### How filtering works

`get_recent_models` only returns first-party, original releases — not raw API
output:
- **Variant filtering**: excludes anything declaring a `base_model`
  relationship on the Hub (fine-tunes, quantizations, adapters, merges). This
  is a real Hub metadata tag, not a name-guessing heuristic.
- **Seen-model tracking**: every model it returns gets recorded in
  `seen_models.json` (gitignored, local state) and is never reported again.
  Combined with the discover-models skill's rule to skip `send_digest`
  entirely when nothing new remains, this means **you only get an email when
  there's something genuinely new to see** — no "nothing new today" spam, no
  re-notifications for a model you've already been told about.

If you delete `seen_models.json`, the next run treats everything currently
within the time window as new again.

### Running on a schedule (e.g. GitHub Actions)

`seen_models.json` is what makes "only email me once per model" work — but it
only works if that file persists between runs. A GitHub Actions runner is a
fresh VM every time, so without extra steps it resets to empty on each
scheduled run and the dedup does nothing. If you wire this up as a scheduled
workflow, cache the file between runs (e.g. `actions/cache` keyed on a fixed
key, restoring/saving `model-scout/seen_models.json`) or commit it back to the
repo at the end of the job. Also remember: a hosted local server
(`MODEL_PROVIDER=local`) isn't reachable from a GitHub-hosted runner — use
`anthropic`, `azure`, or `gemini` for anything running off your own machine.

### Terminal chat UI

Start the API server:

```bash
python app.py
```

Then start the terminal chat:

```bash
python chat_cli.py
```

Type `exit` to quit.

## Verified with

```
deepagents==0.6.12
langchain==1.3.14
langchain-anthropic==1.4.8
langchain-openai==1.3.5
langchain-google-genai==4.2.7
langgraph==1.2.9
huggingface_hub==1.24.0
fastapi==0.115.0
uvicorn==0.32.0
markdown==3.10.2
rich==15.0.0
```

The Hugging Face tool calls and the agent build were run and confirmed working.
The full LLM turn needs your own API key / endpoint.
