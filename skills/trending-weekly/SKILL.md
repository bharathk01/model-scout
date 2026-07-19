---
name: trending-weekly
description: Use when the user wants a roundup of what is currently trending on Hugging Face, rather than what is brand new.
---

# Trending Weekly Roundup

Goal: a "what's hot right now" digest, useful as a weekly pulse-check.

Steps:
1. Confirm the task filter(s). Default: `text-generation` and `text-to-image`.
2. For each, call `get_trending_models`.
3. Hand the results to the `curator` subagent; ask it to write a one-line
   "why it's trending / what it's for" note per model, top 5 per task.
4. Assemble a digest titled "Trending on Hugging Face — week of <date>".
5. Call `send_digest`.

This skill exists to show the point of skills-as-data: it reuses the exact
same tools and subagent as `new-models-digest`. The only new thing added to
the system is this file.
