#!/usr/bin/env python3
"""
🤖 Personal AI Coding Assistant v2.0
Round-robin across multiple OpenRouter API keys
Rich Markdown rendering, prompt_toolkit input, file context,
code extraction, session management, and more.
"""

import os
import re
import json
import sys
import subprocess
import time
import shutil
from datetime import datetime
from pathlib import Path

REQUIRED_PACKAGES = ["openai", "rich", "prompt_toolkit", "python-dotenv", "pyperclip"]

try:
    from openai import OpenAI
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.panel import Panel
    from rich.table import Table
    from rich.syntax import Syntax
    from rich.text import Text
    from rich import print as rprint
    from dotenv import load_dotenv
    from prompt_toolkit import PromptSession
    from prompt_toolkit.history import FileHistory
    from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
    from prompt_toolkit.completion import WordCompleter
    from prompt_toolkit.formatted_text import HTML
except ImportError:
    print("Installing required packages...")
    subprocess.run(
        [sys.executable, "-m", "pip", "install", *REQUIRED_PACKAGES, "--break-system-packages"],
        check=True,
    )
    from openai import OpenAI
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.panel import Panel
    from rich.table import Table
    from rich.syntax import Syntax
    from rich.text import Text
    from rich import print as rprint
    from dotenv import load_dotenv
    from prompt_toolkit import PromptSession
    from prompt_toolkit.history import FileHistory
    from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
    from prompt_toolkit.completion import WordCompleter
    from prompt_toolkit.formatted_text import HTML

# Optional clipboard support
try:
    import pyperclip
    HAS_CLIPBOARD = True
except Exception:
    HAS_CLIPBOARD = False

# ─────────────────────────────────────────────
# 🔑 ADD YOUR OPENROUTER API KEYS HERE
# Get free keys at: https://openrouter.ai
# You can add as many as you want!
# ─────────────────────────────────────────────
API_KEYS = [
    "sk-or-v1-YOUR_FIRST_KEY_HERE",
    "sk-or-v1-YOUR_SECOND_KEY_HERE",
    "sk-or-v1-YOUR_THIRD_KEY_HERE",
    # Add more keys below:
    # "sk-or-v1-YOUR_FOURTH_KEY_HERE",
]

# Load additional keys from a .env file (OPENROUTER_KEYS=key1,key2,key3)
load_dotenv()
_env_keys = os.getenv("OPENROUTER_KEYS", "")
if _env_keys:
    for _k in _env_keys.split(","):
        _k = _k.strip()
        if _k and _k not in API_KEYS:
            API_KEYS.append(_k)

# ─────────────────────────────────────────────
# 🤖 FREE MODELS ON OPENROUTER (updated 2026)
# These rotate alongside keys for extra coverage
# ─────────────────────────────────────────────
FREE_MODELS = [
    "meta-llama/llama-4-maverick:free",
    "meta-llama/llama-4-scout:free",
    "deepseek/deepseek-r1:free",
    "google/gemma-3-27b-it:free",
    "qwen/qwen2.5-72b-instruct:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "mistralai/mistral-small-3.1-24b-instruct:free",
    "google/gemini-2.0-flash-exp:free",
]

SYSTEM_PROMPT = """You are an expert AI coding assistant running on Ubuntu Linux.
You help the user write, debug, explain, and improve code.
When creating files or projects, provide complete working code.
When explaining, be clear and beginner-friendly.
Format code blocks properly with the correct language tag.
If asked to create files, show the complete file content clearly."""

# ─────────────────────────────────────────────
# State & Config
# ─────────────────────────────────────────────
console = Console()
conversation_history: list[dict] = []
current_key_index = 0
current_model_index = 0
key_usage: dict[int, int] = {i: 0 for i in range(len(API_KEYS))}
last_response: str = ""

DATA_DIR = Path.home() / ".myassistant"
DATA_DIR.mkdir(exist_ok=True)
HISTORY_FILE = DATA_DIR / "history.json"
SESSIONS_DIR = DATA_DIR / "sessions"
SESSIONS_DIR.mkdir(exist_ok=True)
INPUT_HISTORY_FILE = str(DATA_DIR / "input_history")

# User-tweakable settings
settings: dict = {
    "temperature": 0.7,
    "max_tokens": 4096,
    "render_markdown": True,
    "pinned_model": None,        # None = round-robin, else a model string
    "stream": True,
    "auto_save": True,
}


# ═════════════════════════════════════════════
# Key / Model rotation
# ═════════════════════════════════════════════

def _valid_keys() -> list[tuple[int, str]]:
    return [(i, k) for i, k in enumerate(API_KEYS) if not k.endswith("_HERE")]


def get_next_key_and_model() -> tuple[str, str]:
    """Round-robin: rotate key AND model together"""
    global current_key_index, current_model_index

    valid = _valid_keys()
    if not valid:
        console.print("[bold red]❌ No valid API keys found! Edit myassistant.py or .env.[/bold red]")
        sys.exit(1)

    idx = current_key_index % len(valid)
    key_pos, key = valid[idx]

    if settings["pinned_model"]:
        model = settings["pinned_model"]
    else:
        model = FREE_MODELS[current_model_index % len(FREE_MODELS)]
        current_model_index = (current_model_index + 1) % len(FREE_MODELS)

    current_key_index = (current_key_index + 1) % len(valid)
    key_usage[key_pos] = key_usage.get(key_pos, 0) + 1

    return key, model


# ═════════════════════════════════════════════
# Chat
# ═════════════════════════════════════════════

def chat_with_ai(user_message: str, retry_count: int = 0) -> str | None:
    """Send message to AI with round-robin key/model rotation and streaming."""
    global last_response
    valid = _valid_keys()
    max_retries = len(valid) * len(FREE_MODELS)

    if retry_count >= max_retries:
        console.print("[bold red]❌ All keys/models exhausted. Wait a moment and retry.[/bold red]")
        return None

    conversation_history.append({"role": "user", "content": user_message})

    key, model = get_next_key_and_model()
    key_preview = key[-8:] if len(key) > 8 else key
    model_short = model.split("/")[-1].replace(":free", "")
    console.print(f"[dim]🔄 Model: {model_short} | Key: …{key_preview}[/dim]")

    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=key)
    t0 = time.time()

    try:
        kwargs = dict(
            model=model,
            messages=[{"role": "system", "content": SYSTEM_PROMPT}, *conversation_history],
            max_tokens=settings["max_tokens"],
            temperature=settings["temperature"],
            stream=settings["stream"],
        )

        if settings["stream"]:
            stream = client.chat.completions.create(**kwargs)
            full_response = ""
            for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta.content
                if delta:
                    print(delta, end="", flush=True)
                    full_response += delta
            print()  # newline after stream

        else:
            resp = client.chat.completions.create(**kwargs)
            full_response = resp.choices[0].message.content or ""

        elapsed = time.time() - t0
        char_count = len(full_response)
        console.print(f"[dim]⏱ {elapsed:.1f}s | ~{char_count} chars[/dim]")

        # Optionally render the full response as Markdown
        if settings["render_markdown"] and full_response.strip():
            console.print()
            console.print(Markdown(full_response))

        conversation_history.append({"role": "assistant", "content": full_response})
        last_response = full_response
        return full_response

    except Exception as e:
        error_msg = str(e)
        conversation_history.pop()  # remove the user message
        rate_keywords = ("rate", "limit", "429", "too many", "quota", "capacity")
        if any(kw in error_msg.lower() for kw in rate_keywords):
            console.print(f"[yellow]⚠️  Rate-limited, rotating… ({retry_count + 1}/{max_retries})[/yellow]")
            return chat_with_ai(user_message, retry_count + 1)
        else:
            console.print(f"[red]❌ Error: {error_msg}[/red]")
            return None


# ═════════════════════════════════════════════
# History / Sessions
# ═════════════════════════════════════════════

def save_history(path: Path | None = None):
    target = path or HISTORY_FILE
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "w") as f:
        json.dump(conversation_history, f, indent=2)
    console.print(f"[green]💾 Saved ({len(conversation_history)} msgs) → {target}[/green]")


def load_history(path: Path | None = None):
    global conversation_history
    target = path or HISTORY_FILE
    if not target.exists():
        console.print("[yellow]No history found at that path.[/yellow]")
        return
    with open(target, "r") as f:
        conversation_history = json.load(f)
    console.print(f"[green]📂 Loaded {len(conversation_history)} messages from {target.name}[/green]")


def session_save(name: str):
    p = SESSIONS_DIR / f"{name}.json"
    save_history(p)


def session_load(name: str):
    p = SESSIONS_DIR / f"{name}.json"
    load_history(p)


def session_list():
    files = sorted(SESSIONS_DIR.glob("*.json"))
    if not files:
        console.print("[yellow]No saved sessions.[/yellow]")
        return
    table = Table(title="Saved Sessions", border_style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Messages", justify="right")
    table.add_column("Modified", style="dim")
    for f in files:
        data = json.loads(f.read_text())
        mtime = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        table.add_row(f.stem, str(len(data)), mtime)
    console.print(table)


def session_delete(name: str):
    p = SESSIONS_DIR / f"{name}.json"
    if p.exists():
        p.unlink()
        console.print(f"[green]🗑 Session '{name}' deleted.[/green]")
    else:
        console.print(f"[red]Session '{name}' not found.[/red]")


# ═════════════════════════════════════════════
# File Context
# ═════════════════════════════════════════════

def read_file_context(filepath: str) -> str | None:
    p = Path(filepath).expanduser().resolve()
    if not p.is_file():
        console.print(f"[red]File not found: {p}[/red]")
        return None
    try:
        content = p.read_text(errors="replace")
        size_kb = p.stat().st_size / 1024
        if size_kb > 100:
            console.print(f"[yellow]⚠️  Large file ({size_kb:.1f} KB). Truncating to first 200 lines.[/yellow]")
            content = "\n".join(content.splitlines()[:200])
        console.print(f"[green]📎 Attached {p.name} ({len(content.splitlines())} lines)[/green]")
        return f"Content of file `{p.name}`:\n```\n{content}\n```"
    except Exception as e:
        console.print(f"[red]Cannot read file: {e}[/red]")
        return None


# ═════════════════════════════════════════════
# Code Extraction
# ═════════════════════════════════════════════

CODE_BLOCK_RE = re.compile(r"```(\w+)?\n(.*?)```", re.DOTALL)


def extract_code_blocks(text: str) -> list[tuple[str, str]]:
    """Return list of (language, code) tuples from markdown code blocks."""
    return [(m.group(1) or "txt", m.group(2).strip()) for m in CODE_BLOCK_RE.finditer(text)]


def extract_command(args: str):
    """Extract code blocks from last response and save to files."""
    if not last_response:
        console.print("[yellow]No response to extract from.[/yellow]")
        return

    blocks = extract_code_blocks(last_response)
    if not blocks:
        console.print("[yellow]No code blocks found in the last response.[/yellow]")
        return

    dest = Path(args).expanduser() if args.strip() else Path.cwd()
    dest.mkdir(parents=True, exist_ok=True)

    LANG_EXT = {
        "python": ".py", "py": ".py", "javascript": ".js", "js": ".js",
        "typescript": ".ts", "ts": ".ts", "html": ".html", "css": ".css",
        "bash": ".sh", "sh": ".sh", "json": ".json", "yaml": ".yaml",
        "yml": ".yaml", "sql": ".sql", "c": ".c", "cpp": ".cpp",
        "java": ".java", "go": ".go", "rust": ".rs", "ruby": ".rb",
        "txt": ".txt", "xml": ".xml", "toml": ".toml", "md": ".md",
        "dockerfile": ".Dockerfile", "makefile": "Makefile",
    }

    for i, (lang, code) in enumerate(blocks, 1):
        ext = LANG_EXT.get(lang.lower(), f".{lang}")
        filename = dest / f"extracted_{i}{ext}"
        filename.write_text(code + "\n")
        console.print(f"  [green]📄 {filename}[/green] ({lang}, {len(code.splitlines())} lines)")

    console.print(f"[green]✅ Extracted {len(blocks)} code block(s) → {dest}[/green]")


# ═════════════════════════════════════════════
# Clipboard
# ═════════════════════════════════════════════

def copy_last_response():
    if not last_response:
        console.print("[yellow]Nothing to copy.[/yellow]")
        return
    if HAS_CLIPBOARD:
        try:
            pyperclip.copy(last_response)
            console.print("[green]📋 Last response copied to clipboard.[/green]")
            return
        except Exception:
            pass
    # Fallback: try xclip / xsel
    for tool in ("xclip -selection clipboard", "xsel --clipboard --input"):
        try:
            subprocess.run(tool.split(), input=last_response.encode(), check=True)
            console.print("[green]📋 Copied to clipboard.[/green]")
            return
        except Exception:
            continue
    console.print("[red]Clipboard not available. Install xclip or pyperclip.[/red]")


# ═════════════════════════════════════════════
# Export conversation
# ═════════════════════════════════════════════

def export_markdown(filepath: str = ""):
    p = Path(filepath).expanduser() if filepath.strip() else Path.cwd() / "conversation.md"
    lines = [f"# Conversation Export — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"]
    for msg in conversation_history:
        role = msg["role"].capitalize()
        lines.append(f"## {role}\n\n{msg['content']}\n\n---\n")
    p.write_text("\n".join(lines))
    console.print(f"[green]📝 Exported to {p}[/green]")


# ═════════════════════════════════════════════
# Settings
# ═════════════════════════════════════════════

def handle_set(args: str):
    parts = args.strip().split(None, 1)
    if len(parts) < 2:
        # Show all settings
        table = Table(title="Settings", border_style="cyan")
        table.add_column("Key", style="green")
        table.add_column("Value", style="yellow")
        for k, v in settings.items():
            table.add_row(k, str(v))
        console.print(table)
        return

    key, val = parts[0], parts[1]
    if key not in settings:
        console.print(f"[red]Unknown setting: {key}[/red]")
        console.print(f"[dim]Available: {', '.join(settings.keys())}[/dim]")
        return

    # Type-aware parsing
    cur = settings[key]
    if isinstance(cur, bool) or cur is None and key in ("render_markdown", "stream", "auto_save"):
        settings[key] = val.lower() in ("true", "1", "yes", "on")
    elif isinstance(cur, float):
        settings[key] = float(val)
    elif isinstance(cur, int):
        settings[key] = int(val)
    elif key == "pinned_model":
        settings[key] = None if val.lower() in ("none", "auto", "off") else val
    else:
        settings[key] = val

    console.print(f"[green]✅ {key} = {settings[key]}[/green]")


# ═════════════════════════════════════════════
# Usage stats
# ═════════════════════════════════════════════

def show_usage():
    table = Table(title="📊 Key Usage Stats", border_style="cyan")
    table.add_column("#", justify="right", style="dim")
    table.add_column("Key", style="green")
    table.add_column("Requests", justify="right", style="yellow")
    for pos, key in _valid_keys():
        preview = f"…{key[-8:]}"
        table.add_row(str(pos + 1), preview, str(key_usage.get(pos, 0)))
    console.print(table)


# ═════════════════════════════════════════════
# Help
# ═════════════════════════════════════════════

def show_help():
    help_md = """
## 📖 Commands

| Command | Description |
|---------|-------------|
| `/help` | Show this help |
| `/clear` | Clear conversation history |
| `/save` | Save conversation to default file |
| `/load` | Load previous conversation |
| `/export [path]` | Export conversation as Markdown |
| `/usage` | Show API key usage stats |
| `/keys` | Show how many keys are loaded |
| `/models` | List available free models |
| `/model <name>` | Pin a specific model (or `auto` to unpin) |
| `/set [key] [value]` | View or change settings |
| `/file <path>` | Attach file content to next message |
| `/extract [dir]` | Save code blocks from last response |
| `/copy` | Copy last response to clipboard |
| `/session list` | List saved sessions |
| `/session save <n>` | Save current session by name |
| `/session load <n>` | Load a saved session |
| `/session delete <n>` | Delete a saved session |
| `/multi` | Enter multi-line input (end with `END` on its own line) |
| `/quit` | Exit the assistant |

## 💡 Example prompts

- *"Create a Python Flask web app with login"*
- *"Fix the bug in this code: \\[paste code\\]"*
- *"Explain what this script does: \\[paste code\\]"*
- *"/file ./app.py" then "Refactor this to use async"*
"""
    console.print(Panel(Markdown(help_md), title="Help", border_style="cyan"))


# ═════════════════════════════════════════════
# Banner
# ═════════════════════════════════════════════

def show_banner():
    banner = """[bold cyan]
  ╔════════════════════════════════════════════╗
  ║   🤖 Personal AI Coding Assistant  v2.0   ║
  ║       OpenRouter Round-Robin Edition       ║
  ╚════════════════════════════════════════════╝[/bold cyan]"""
    console.print(banner)

    valid = _valid_keys()
    console.print(f"  [green]✅ {len(valid)} API key(s) loaded[/green]")
    console.print(f"  [green]✅ {len(FREE_MODELS)} free models available[/green]")
    pinned = settings["pinned_model"]
    if pinned:
        console.print(f"  [yellow]📌 Pinned model: {pinned}[/yellow]")
    console.print(f"  [dim]Type /help for commands • Start typing to chat![/dim]\n")


# ═════════════════════════════════════════════
# Multi-line input helper
# ═════════════════════════════════════════════

def get_multiline_input() -> str:
    console.print("[dim]Enter multi-line text. Type END on its own line to finish.[/dim]")
    lines = []
    while True:
        try:
            line = input("... ")
        except EOFError:
            break
        if line.strip() == "END":
            break
        lines.append(line)
    return "\n".join(lines)


# ═════════════════════════════════════════════
# Main loop
# ═════════════════════════════════════════════

def main():
    show_banner()

    valid = _valid_keys()
    if not valid:
        console.print(Panel(
            "[bold red]No API keys configured![/bold red]\n\n"
            "1. Edit [cyan]myassistant.py[/cyan] → fill [yellow]API_KEYS[/yellow]\n"
            "2. Or create a [cyan].env[/cyan] file with OPENROUTER_KEYS=key1,key2\n"
            "3. Get free keys at: [link]https://openrouter.ai[/link]",
            title="⚠️  Setup Required",
            border_style="red",
        ))
        sys.exit(1)

    # prompt_toolkit session with history & auto-complete for commands
    cmd_completer = WordCompleter(
        ["/help", "/clear", "/save", "/load", "/export", "/usage", "/keys",
         "/models", "/model", "/set", "/file", "/extract", "/copy",
         "/session", "/multi", "/quit", "/exit"],
        sentence=True,
    )
    session = PromptSession(
        history=FileHistory(INPUT_HISTORY_FILE),
        auto_suggest=AutoSuggestFromHistory(),
        completer=cmd_completer,
    )

    pending_file_context: str | None = None

    while True:
        try:
            user_input = session.prompt(
                HTML("<ansigreen><b>You ▶ </b></ansigreen>"),
            ).strip()

            if not user_input:
                continue

            # ── Commands ────────────────────────
            if user_input.startswith("/"):
                parts = user_input.split(None, 1)
                cmd = parts[0].lower()
                arg = parts[1] if len(parts) > 1 else ""

                if cmd in ("/quit", "/exit"):
                    if settings["auto_save"] and conversation_history:
                        save_history()
                    console.print("[yellow]👋 Goodbye![/yellow]")
                    break

                elif cmd == "/clear":
                    conversation_history.clear()
                    console.print("[green]✅ Conversation cleared![/green]")

                elif cmd == "/save":
                    save_history()

                elif cmd == "/load":
                    load_history()

                elif cmd == "/export":
                    export_markdown(arg)

                elif cmd == "/usage":
                    show_usage()

                elif cmd == "/help":
                    show_help()

                elif cmd == "/keys":
                    console.print(f"[cyan]🔑 {len(_valid_keys())} valid key(s) rotating[/cyan]")

                elif cmd == "/models":
                    console.print("[cyan]🤖 Free models in rotation:[/cyan]")
                    for i, m in enumerate(FREE_MODELS, 1):
                        pinned = " [yellow]← pinned[/yellow]" if m == settings["pinned_model"] else ""
                        console.print(f"  {i}. {m}{pinned}")

                elif cmd == "/model":
                    if not arg or arg.lower() in ("auto", "none", "off"):
                        settings["pinned_model"] = None
                        console.print("[green]✅ Model unpinned — back to round-robin.[/green]")
                    else:
                        # Allow selecting by number
                        if arg.isdigit():
                            idx = int(arg) - 1
                            if 0 <= idx < len(FREE_MODELS):
                                arg = FREE_MODELS[idx]
                            else:
                                console.print(f"[red]Invalid model number. Choose 1-{len(FREE_MODELS)}.[/red]")
                                continue
                        settings["pinned_model"] = arg
                        console.print(f"[green]📌 Pinned model: {arg}[/green]")

                elif cmd == "/set":
                    handle_set(arg)

                elif cmd == "/file":
                    if not arg:
                        console.print("[red]Usage: /file <path>[/red]")
                    else:
                        ctx = read_file_context(arg)
                        if ctx:
                            pending_file_context = ctx

                elif cmd == "/extract":
                    extract_command(arg)

                elif cmd == "/copy":
                    copy_last_response()

                elif cmd == "/session":
                    sub_parts = arg.split(None, 1)
                    sub_cmd = sub_parts[0].lower() if sub_parts else ""
                    sub_arg = sub_parts[1].strip() if len(sub_parts) > 1 else ""
                    if sub_cmd == "list":
                        session_list()
                    elif sub_cmd == "save" and sub_arg:
                        session_save(sub_arg)
                    elif sub_cmd == "load" and sub_arg:
                        session_load(sub_arg)
                    elif sub_cmd == "delete" and sub_arg:
                        session_delete(sub_arg)
                    else:
                        console.print("[yellow]Usage: /session list | save <name> | load <name> | delete <name>[/yellow]")

                elif cmd == "/multi":
                    text = get_multiline_input()
                    if text.strip():
                        user_input = text  # fall through to send to AI
                    else:
                        continue

                else:
                    console.print(f"[red]Unknown command: {cmd}. Type /help for commands.[/red]")
                    continue

                # If the command didn't set user_input to a chat message, continue
                if user_input.startswith("/") and cmd != "/multi":
                    continue

            # ── Prepend file context if attached ──
            message = user_input
            if pending_file_context:
                message = f"{pending_file_context}\n\n{user_input}"
                pending_file_context = None

            # ── Send to AI ──────────────────────
            console.print("\n[bold blue]🤖 Assistant[/bold blue]")
            response = chat_with_ai(message)
            if response:
                console.print("[dim]" + "─" * min(console.width, 70) + "[/dim]")

        except KeyboardInterrupt:
            if settings["auto_save"] and conversation_history:
                save_history()
            console.print("\n[yellow]👋 Goodbye![/yellow]")
            break
        except EOFError:
            break
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")


if __name__ == "__main__":
    main()
