#!/usr/bin/env python3
"""
🤖 Personal AI Coding Assistant
Round-robin across multiple OpenRouter API keys
"""

import os
import json
import sys
import subprocess
from datetime import datetime
from pathlib import Path

try:
    from openai import OpenAI
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.panel import Panel
    from rich.prompt import Prompt
    from rich.text import Text
    from rich import print as rprint
    from dotenv import load_dotenv
except ImportError:
    print("Installing required packages...")
    subprocess.run([sys.executable, "-m", "pip", "install", "openai", "rich", "prompt_toolkit", "python-dotenv", "--break-system-packages"], check=True)
    from openai import OpenAI
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.panel import Panel
    from rich.prompt import Prompt
    from rich.text import Text
    from rich import print as rprint
    from dotenv import load_dotenv

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
# 🤖 FREE MODELS ON OPENROUTER
# These rotate alongside keys for extra coverage
# ─────────────────────────────────────────────
FREE_MODELS = [
    "meta-llama/llama-3.3-70b-instruct:free",
    "google/gemma-3-27b-it:free",
    "deepseek/deepseek-r1:free",
    "mistralai/mistral-7b-instruct:free",
    "qwen/qwen2.5-72b-instruct:free",
]

SYSTEM_PROMPT = """You are an expert AI coding assistant running on Ubuntu Linux.
You help the user write, debug, explain, and improve code.
When creating files or projects, provide complete working code.
When explaining, be clear and beginner-friendly.
Format code blocks properly with the correct language tag.
If asked to create files, show the complete file content clearly."""

# ─────────────────────────────────────────────
# State
# ─────────────────────────────────────────────
console = Console()
conversation_history = []
current_key_index = 0
current_model_index = 0
key_usage = {i: 0 for i in range(len(API_KEYS))}
HISTORY_FILE = Path.home() / ".myassistant_history.json"


def get_next_key_and_model():
    """Round-robin: rotate key AND model together"""
    global current_key_index, current_model_index
    
    # Filter out placeholder keys
    valid_keys = [(i, k) for i, k in enumerate(API_KEYS) if not k.endswith("_HERE")]
    
    if not valid_keys:
        console.print("[bold red]❌ No valid API keys found! Please edit myassistant.py and add your OpenRouter keys.[/bold red]")
        console.print("[yellow]👉 Get free keys at: https://openrouter.ai[/yellow]")
        sys.exit(1)
    
    # Pick key using round-robin
    idx = current_key_index % len(valid_keys)
    key_pos, key = valid_keys[idx]
    model = FREE_MODELS[current_model_index % len(FREE_MODELS)]
    
    # Increment for next call
    current_key_index = (current_key_index + 1) % len(valid_keys)
    current_model_index = (current_model_index + 1) % len(FREE_MODELS)
    key_usage[key_pos] += 1
    
    return key, model


def chat_with_ai(user_message, retry_count=0):
    """Send message to AI with round-robin key/model rotation and streaming"""
    valid_keys = [k for k in API_KEYS if not k.endswith("_HERE")]
    max_retries = len(valid_keys)

    if retry_count >= max_retries:
        console.print("[bold red]❌ All keys are rate-limited. Please wait a moment and try again.[/bold red]")
        return None

    conversation_history.append({"role": "user", "content": user_message})

    key, model = get_next_key_and_model()

    # Show which key/model is being used
    key_preview = key[-8:] if len(key) > 8 else key
    console.print(f"[dim]🔄 Using model: {model.split('/')[1]} | Key: ...{key_preview}[/dim]")

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=key,
    )

    try:
        stream = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                *conversation_history
            ],
            max_tokens=4096,
            stream=True,
        )

        full_response = ""
        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                print(delta, end="", flush=True)
                full_response += delta
        print()  # newline after stream ends

        conversation_history.append({"role": "assistant", "content": full_response})
        return full_response

    except Exception as e:
        error_msg = str(e)
        conversation_history.pop()  # remove the user message added above
        if "rate" in error_msg.lower() or "limit" in error_msg.lower() or "429" in error_msg:
            console.print(f"[yellow]⚠️  Key rate limited, trying next key... ({retry_count + 1}/{max_retries})[/yellow]")
            return chat_with_ai(user_message, retry_count + 1)
        else:
            return f"❌ Error: {error_msg}"


def save_history():
    """Save conversation to file"""
    with open(HISTORY_FILE, "w") as f:
        json.dump(conversation_history, f, indent=2)
    console.print(f"[green]💾 Conversation saved to {HISTORY_FILE}[/green]")


def load_history():
    """Load previous conversation"""
    global conversation_history
    if HISTORY_FILE.exists():
        with open(HISTORY_FILE, "r") as f:
            conversation_history = json.load(f)
        console.print(f"[green]📂 Loaded {len(conversation_history)} messages from history[/green]")
    else:
        console.print("[yellow]No previous history found. Starting fresh.[/yellow]")


def show_usage():
    """Show key usage stats"""
    console.print("\n[bold cyan]📊 Key Usage Stats:[/bold cyan]")
    valid_keys = [(i, k) for i, k in enumerate(API_KEYS) if not k.endswith("_HERE")]
    for pos, key in valid_keys:
        preview = f"...{key[-8:]}"
        usage = key_usage.get(pos, 0)
        console.print(f"  Key {pos+1} ({preview}): [green]{usage} requests[/green]")


def show_help():
    help_text = """
[bold cyan]📖 Commands:[/bold cyan]

  [green]/help[/green]          - Show this help
  [green]/clear[/green]         - Clear conversation history
  [green]/save[/green]          - Save conversation to file
  [green]/load[/green]          - Load previous conversation
  [green]/usage[/green]         - Show API key usage stats
  [green]/keys[/green]          - Show how many keys are loaded
  [green]/models[/green]        - Show available free models
  [green]/quit[/green]          - Exit the assistant

[bold cyan]💡 Example prompts:[/bold cyan]

  "Create a Python Flask web app with login"
  "Fix the bug in this code: [paste code]"
  "Explain what this script does: [paste code]"
  "Create a todo app and save it to ~/todo-app/"
  "Write a bash script to backup my home folder"
    """
    console.print(Panel(help_text, title="Help", border_style="cyan"))


def show_banner():
    banner = """[bold cyan]
  ╔═══════════════════════════════════════╗
  ║     🤖 Personal AI Coding Assistant   ║
  ║     OpenRouter Round-Robin Edition    ║
  ╚═══════════════════════════════════════╝[/bold cyan]"""
    console.print(banner)
    
    valid_keys = [k for k in API_KEYS if not k.endswith("_HERE")]
    console.print(f"[green]✅ Loaded {len(valid_keys)} API key(s)[/green]")
    console.print(f"[green]✅ {len(FREE_MODELS)} free models available[/green]")
    console.print(f"[dim]Type /help for commands | Type your coding question to start![/dim]\n")


def main():
    show_banner()
    
    # Check if any real keys are configured
    valid_keys = [k for k in API_KEYS if not k.endswith("_HERE")]
    if not valid_keys:
        console.print(Panel(
            "[bold red]No API keys configured![/bold red]\n\n"
            "1. Open [cyan]myassistant.py[/cyan] in a text editor\n"
            "2. Find the [yellow]API_KEYS[/yellow] section at the top\n"
            "3. Replace [yellow]sk-or-v1-YOUR_FIRST_KEY_HERE[/yellow] with your real key\n"
            "4. Get free keys at: [link]https://openrouter.ai[/link]",
            title="⚠️  Setup Required",
            border_style="red"
        ))
        sys.exit(1)
    
    while True:
        try:
            # Get user input
            user_input = Prompt.ask("\n[bold green]You[/bold green]").strip()
            
            if not user_input:
                continue
            
            # Handle commands
            if user_input.startswith("/"):
                cmd = user_input.lower()
                if cmd == "/quit" or cmd == "/exit":
                    console.print("[yellow]👋 Goodbye![/yellow]")
                    break
                elif cmd == "/clear":
                    conversation_history.clear()
                    console.print("[green]✅ Conversation cleared![/green]")
                elif cmd == "/save":
                    save_history()
                elif cmd == "/load":
                    load_history()
                elif cmd == "/usage":
                    show_usage()
                elif cmd == "/help":
                    show_help()
                elif cmd == "/keys":
                    valid = [k for k in API_KEYS if not k.endswith("_HERE")]
                    console.print(f"[cyan]🔑 {len(valid)} valid key(s) loaded and rotating[/cyan]")
                elif cmd == "/models":
                    console.print("[cyan]🤖 Free models in rotation:[/cyan]")
                    for m in FREE_MODELS:
                        console.print(f"  • {m}")
                else:
                    console.print(f"[red]Unknown command: {user_input}. Type /help for commands.[/red]")
                continue
            
            # Send to AI
            console.print("\n[bold blue]🤖 Assistant[/bold blue]")
            response = chat_with_ai(user_input)
            if response:
                console.print("[dim]─" * 60 + "[/dim]")
            
        except KeyboardInterrupt:
            console.print("\n[yellow]👋 Goodbye![/yellow]")
            break
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")


if __name__ == "__main__":
    main()
