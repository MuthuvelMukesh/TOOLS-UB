# 🤖 Personal AI Coding Assistant v2.0

A feature-rich CLI coding assistant powered by [OpenRouter](https://openrouter.ai) free models, with round-robin key/model rotation, Rich Markdown rendering, prompt\_toolkit input, file context injection, code extraction, session management, and more.

## What's New in v2.0

- **Rich Markdown rendering** — AI responses are rendered as beautiful formatted Markdown in the terminal
- **prompt\_toolkit input** — Command auto-complete, persistent input history, and auto-suggestions
- **File context injection** — Attach any file to your next message with `/file <path>`
- **Code extraction** — Save code blocks from responses to files with `/extract`
- **Session management** — Save, load, list, and delete named sessions
- **Model pinning** — Pin a specific model or let it round-robin with `/model`
- **Configurable settings** — Adjust temperature, max tokens, streaming, markdown rendering via `/set`
- **Multi-line input** — Paste multi-line code with `/multi`
- **Clipboard copy** — Copy the last response with `/copy`
- **Markdown export** — Export full conversation as `.md` with `/export`
- **Response timing** — See response time and character count after each reply
- **Auto-save on exit** — Conversation is saved automatically when you quit
- **Updated model list** — Llama 4, Gemini 2.0 Flash, Mistral Small 3.1, and more

## Features

- **Round-robin key & model rotation** — Distributes requests across multiple API keys and free models
- **Rich terminal UI** — Beautiful formatted output using the `rich` library
- **Persistent conversation history** — Across sessions with auto-save
- **Named sessions** — Organize conversations by project or topic
- **CLI command expert** (`check.py`) — Can suggest and execute terminal commands directly
- **`.env` support** — Load API keys securely from a `.env` file

## Files

| File | Description |
|------|-------------|
| `myassistant.py` | Core AI coding assistant v2.0 with all features |
| `check.py` | Extended assistant with CLI command suggestion & execution |

## Setup

### 1. Install dependencies

```bash
pip install openai rich prompt_toolkit python-dotenv pyperclip
```

> Dependencies are also auto-installed on first run.

### 2. Add your OpenRouter API keys

Edit `myassistant.py` (or `check.py`) and replace the placeholder keys:

```python
API_KEYS = [
    "sk-or-v1-YOUR_FIRST_KEY_HERE",
    "sk-or-v1-YOUR_SECOND_KEY_HERE",
]
```

Get free API keys at: [https://openrouter.ai](https://openrouter.ai)

### 3. (Optional) Use a `.env` file

Create a `.env` file in the project directory:

```
OPENROUTER_KEYS=sk-or-v1-key1,sk-or-v1-key2,sk-or-v1-key3
```

## Usage

### AI Coding Assistant

```bash
python myassistant.py
```

### CLI Command Expert

```bash
python check.py
```

### Commands Reference

| Command | Description |
|---------|-------------|
| `/help` | Show help |
| `/clear` | Clear conversation |
| `/save` / `/load` | Save/load default history |
| `/export [path]` | Export conversation as Markdown |
| `/usage` | API key usage stats |
| `/keys` / `/models` | Show loaded keys and models |
| `/model <name\|#>` | Pin a model (or `auto` to unpin) |
| `/set [key] [val]` | View/change settings (temperature, max\_tokens, etc.) |
| `/file <path>` | Attach file content to the next message |
| `/extract [dir]` | Save code blocks from last response to files |
| `/copy` | Copy last response to clipboard |
| `/session list\|save\|load\|delete <name>` | Manage named sessions |
| `/multi` | Enter multi-line input (end with `END`) |
| `/quit` | Exit |

## Free Models Used

- `meta-llama/llama-4-maverick:free`
- `meta-llama/llama-4-scout:free`
- `deepseek/deepseek-r1:free`
- `google/gemma-3-27b-it:free`
- `qwen/qwen2.5-72b-instruct:free`
- `meta-llama/llama-3.3-70b-instruct:free`
- `mistralai/mistral-small-3.1-24b-instruct:free`
- `google/gemini-2.0-flash-exp:free`

## Requirements

- Python 3.10+
- Ubuntu / Linux recommended
- OpenRouter API key(s)
