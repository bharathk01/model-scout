"""Simple terminal chat UI for Model Scout."""

import json
import os
import urllib.error
import urllib.request

from rich.console import Console
from rich.markdown import Markdown

API_URL = os.getenv("MODELSCOUT_API_URL", "http://127.0.0.1:8015/ask")
console = Console()


def chat_once(prompt: str) -> str:
    payload = json.dumps({"prompt": prompt}).encode("utf-8")
    req = urllib.request.Request(
        API_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            body = json.loads(response.read().decode("utf-8"))
        return body.get("response", "")
    except urllib.error.HTTPError as exc:
        try:
            detail = json.loads(exc.read().decode("utf-8")).get("detail", exc.reason)
        except (json.JSONDecodeError, UnicodeDecodeError):
            detail = exc.reason
        return f"[server error {exc.code}] {detail}"
    except urllib.error.URLError as exc:
        return f"[could not reach {API_URL}: {exc.reason}] Is `python app.py` running?"


def main() -> None:
    console.print("[bold]Model Scout terminal chat[/bold]")
    console.print("Type 'exit' to quit.\n")
    while True:
        try:
            user_input = console.input("[bold cyan]You:[/bold cyan] ").strip()
        except KeyboardInterrupt:
            console.print("\nGoodbye!")
            break

        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit"}:
            console.print("Goodbye!")
            break

        with console.status("[dim]Thinking...[/dim]", spinner="dots"):
            response = chat_once(user_input)

        console.print("[bold magenta]Model Scout:[/bold magenta]")
        console.print(Markdown(response))
        console.print()


if __name__ == "__main__":
    main()
