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
├── skills/
│   ├── discover-models/SKILL.md          # workflow #1
│   └── discover-trending-models/SKILL.md # workflow #2 — reuses the same tools + subagent
└── .github/workflows/
    └── daily-digest.yml            # runs the agent on a schedule, no server needed
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

Open `.env` and fill in one provider block. The easiest way to get running:
Google Gemini has a genuinely free tier (no card) with a large context
window — get a key at [aistudio.google.com/apikey](https://aistudio.google.com/apikey)
and set:

```ini
MODEL_PROVIDER=gemini
MODEL_NAME=gemini-3.1-flash-lite
GOOGLE_API_KEY=your-key-here
```

(`.env` is gitignored, so your keys never get committed.) A local model is
also supported (see the provider table below) but this agent's full system
prompt + tools + skills is a few thousand tokens before your question even
starts — small local models with a short context window (4-8K) can overflow
on that. Gemini's free tier avoids the problem entirely.

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

Note: a single request can trigger 5-10+ model calls (skill matching, tool
calls, the curator subagent), so on Gemini's free tier, pin `MODEL_NAME` to a
specific stable model rather than a `-latest` alias — those can silently
resolve to a brand-new preview model with a much stricter introductory quota
(as low as 5 requests/minute), which the agent will blow through immediately.
`gemini-3.1-flash-lite` (the default above) is what this repo was verified
against.

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

`get_recent_models` doesn't return raw API output — it applies real signal
filtering before the agent (or curator subagent) ever sees the list:
- **Variant filtering**: Hugging Face auto-tags any model that declares a
  `base_model` relationship (fine-tunes, quantizations, adapters, merges) —
  a real Hub metadata tag, not a name-guessing heuristic. A third-party
  variant with no real traction is dropped as noise. An *official* variant
  (same org as the base model, e.g. the lab's own GGUF build) or a *popular*
  community variant (20+ likes or 1,000+ downloads — see
  `POPULAR_LIKES_THRESHOLD`/`POPULAR_DOWNLOADS_THRESHOLD` in `tools.py`) is
  kept, but labeled `variant of <base>` so it reads as a new build of an
  existing model, not a brand-new one.
- **Seen-model tracking**: every model it returns gets recorded in
  `seen_models.json` (gitignored, local state) and is never reported again.

Combined with the discover-models skill's rule to skip `send_digest` entirely
when nothing new remains, this means **you only get an email when there's
something genuinely new to see** — no "nothing new today" spam, no
re-notifications for a model you've already been told about.

If you delete `seen_models.json`, the next run treats everything currently
within the time window as new again.

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

## Running on a schedule (GitHub Actions)

The actual "production" use case here is a once-a-day batch job, not a
hosted API — so there's no server to deploy. `.github/workflows/daily-digest.yml`
runs `python agent.py "..."` on a schedule and emails you only if something
genuinely new was found. To use it in your own fork:

1. Add these as repo secrets (Settings → Secrets and variables → Actions):
   `GOOGLE_API_KEY`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`,
   `EMAIL_FROM`, `EMAIL_TO`.
2. The schedule is `0 18 * * *` (18:00 UTC = 23:30 IST) — GitHub Actions cron
   is always UTC, so edit the expression if you want a different local time.
3. Trigger it once manually from the Actions tab (**Run workflow**) to
   confirm it works before trusting the schedule.

Two things worth knowing:
- `seen_models.json`'s dedup state persists across runs via `actions/cache`,
  saved under a fresh key each run and restored by prefix match — GitHub's
  cache action silently refuses to overwrite an existing key, so a naive
  fixed-key setup would look like it works but never actually update.
- `MODEL_PROVIDER=local` won't work in CI — a GitHub-hosted runner can't
  reach a server on your machine. The workflow uses `gemini`.

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

Everything in this README has been run end-to-end and confirmed working: the
terminal agent, the FastAPI app, the terminal chat UI, real email delivery,
and the scheduled GitHub Actions workflow (against Google Gemini's free
tier). You'll need your own API key / SMTP credentials to run it yourself —
none are bundled.
