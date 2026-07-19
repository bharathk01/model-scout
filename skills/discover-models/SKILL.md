---
name: new-models-digest
description: Use when the user wants a digest of models newly launched on Hugging Face for one or more tasks (e.g. "any new text-to-image models today?").
---

# New Models Digest

Goal: produce a short, skimmable digest of genuinely worth-knowing-about
models — never a raw API dump, and never noise from anonymous re-uploads.

This is a strict checklist. Do not skip a step, and do not shortcut it just
because the request was phrased loosely (e.g. "get the new models" still
means the full checklist below, not one tool call).

Steps:
1. Determine the task filter(s). If the user named one or more (e.g.
   "text-to-image"), use exactly those. Otherwise you MUST use ALL of these
   four defaults — do not stop at the first one:
   - `text-generation` (also covers reasoning/agentic models — call those out
     by name in the write-up if you recognize them as such)
   - `feature-extraction` (embedding models)
   - `text-to-image`
   - `image-text-to-text` (vision)
2. Time window: last 24 hours, unless the user said otherwise.
3. Call `get_recent_models` once per task from step 1, using exactly those
   pipeline_tag strings — that's up to 4 tool calls, not 1. Do NOT call
   `get_trending_models` as part of this skill; this workflow is about what's
   NEW, not what's popular, and the digest should describe entries as "new" or
   "just released", never as "trending". `get_recent_models` already drops
   low-signal, third-party fine-tunes/quantizations/adapters and anything
   reported in a previous run. What comes back can still include entries
   marked "variant of <base>" — those are official releases (same org as the
   base model, e.g. the lab's own GGUF build) or popular community variants,
   kept because they're worth knowing about. Treat those as "a new build of
   an existing model", not as a brand-new model, when you write them up.
4. You MUST hand the combined raw list to the `curator` subagent before
   writing anything — this step is never optional, regardless of how the
   request was phrased. Do not summarize the raw tool output yourself. Ask
   the curator to:
   - prefer significant releases from organizations or models showing early community interest
   - ignore remaining low-signal personal experiments (e.g. test repos, empty model cards)
   - keep at most the 5 most notable per task
   - write one plain-language line per model on why it might matter, and note
     explicitly when an entry is a variant rather than a new model
5. If, after curation, every task came back with nothing notable, stop here —
   say so in one line and do NOT call `send_digest`. Only genuinely new
   content is worth an email.
6. Otherwise, assemble a digest titled "New on Hugging Face — <date>" with one
   section per task that has results, using the curator's write-up (not the
   raw tool output), and call `send_digest` to deliver it (emails it if SMTP
   is configured, otherwise saves a local copy).

Rules:
- Never invent models.
- Only summarize tool output.
- Keep explanations factual.
- Keep the digest under 200 words.
- Do not call `send_digest` for an empty or "nothing new" digest.
- Do not call `send_digest` with content that skipped the curator step.
