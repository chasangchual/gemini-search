from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from pathlib import Path

from .gemini_client import GeminiClient


HISTORY_FILE = Path.home() / ".gemini_search_history"


def create_key_bindings():
    kb = KeyBindings()

    @kb.add("c-up")
    def _(event):
        event.current_buffer.cursor_up(count=1)

    @kb.add("c-down")
    def _(event):
        event.current_buffer.cursor_down(count=1)

    return kb


def run_repl(client: GeminiClient):
    session = PromptSession(history=FileHistory(str(HISTORY_FILE)))
    print("\nGemini Search REPL")
    print("Type your question and press Enter. Press Ctrl+C or type 'exit' to quit.\n")

    while True:
        try:
            user_input = session.prompt("\n> ").strip()

            if not user_input:
                continue

            if user_input.lower() in ("exit", "quit", "q"):
                print("Goodbye!")
                break

            print()
            response = client.send_message(user_input)

            for chunk in response:
                print(chunk.text, end="", flush=True)
            print()

        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except EOFError:
            print("\nGoodbye!")
            break
