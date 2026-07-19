---
name: new-models-digest
description: Use when the user wants a digest of models newly launched on Hugging Face for one or more tasks (e.g. "any new text-to-image models today?").
---

# New Models Digest

Goal: produce a short, skimmable digest of genuinely new models, not raw API dumps.

Steps:
1. Confirm the task filter(s) with the user. If none given, default to
   `text-generation`. Common tags: `text-generation`, `text-to-image`,
   `automatic-speech-recognition`, `image-text-to-text`.
2. Confirm the time window. Default: last 24 hours.
3. For each task, call `get_recent_models`.
4. Hand the raw list to the `curator` subagent. Ask it to:
   - drop obvious fine-tunes / personal experiments (long random suffixes,
     0 downloads AND 0 likes) unless nothing else is available
   - keep at most the 5 most notable per task
   - write one plain-language line per model on why it might matter
5. Assemble a digest titled "New on Hugging Face — <date>" with one section
   per task.
6. Call `send_digest` to deliver it (emails it if SMTP is configured,
   otherwise saves a local copy).

Keep the whole digest under ~200 words. If a task has nothing new, say so in
one line rather than padding.
