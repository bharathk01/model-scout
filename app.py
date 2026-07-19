"""FastAPI wrapper for the ModelScout agent.

Exposes the same agent built in agent.py over HTTP. It does not talk to a
model directly — every request runs the full DeepAgent (skills, Hugging Face
tools, curator subagent), exactly like `python agent.py "<prompt>"` does.
Digest delivery (email vs local save) is decided by the agent's send_digest
tool, not by this layer.
"""

import logging
import time
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from agent import agent  # noqa: F401 (import order) — also runs configure_logging()

logger = logging.getLogger("modelscout.app")

app = FastAPI(title="Model Scout API", version="1.0.0")


class AskRequest(BaseModel):
    prompt: str = Field(..., min_length=1)

    model_config = {
        "json_schema_extra": {
            "example": {"prompt": "Any new text-to-image models in the last 12 hours?"}
        }
    }


def extract_text(content: Any) -> str:
    """Normalize a message's .content into plain text.

    Some providers (e.g. Gemini, when it makes tool calls) return content as
    a list of blocks (text, tool-call signatures, ...) instead of a plain
    string. We only care about the text parts.
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            block.get("text", "")
            for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        )
    return str(content)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/ask")
def ask(request: AskRequest) -> dict[str, Any]:
    logger.info("Received /ask request prompt=%r", request.prompt)
    started = time.monotonic()

    try:
        result = agent.invoke({"messages": [{"role": "user", "content": request.prompt}]})
        content = extract_text(result["messages"][-1].content)
    except Exception as exc:
        logger.exception("Agent invocation failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    elapsed = time.monotonic() - started
    logger.info("Agent responded in %.1fs, content_length=%d", elapsed, len(content))

    return {"response": content}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="127.0.0.1", port=8015, reload=False)
