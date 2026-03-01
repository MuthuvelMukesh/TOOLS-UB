# 🤖 Personal AI Coding Assistant

A CLI-based personal AI coding assistant powered by [OpenRouter](https://openrouter.ai) free models, with round-robin rotation across multiple API keys and models.

## Features

- **Round-robin key & model rotation** — Distributes requests across multiple OpenRouter API keys and free models to maximize usage limits
- **Rich terminal UI** — Beautiful formatted output using the `rich` library
- **Conversation history** — Persists chat history across sessions
- **CLI command expert** (`check.py`) — Can suggest and execute terminal commands directly
- **`.env` support** — Load API keys securely from a `.env` file

## Files

| File | Description |
|------|-------------|
| `myassistant.py` | Core AI coding assistant with multi-key round-robin |
| `check.py` | Extended assistant with CLI command suggestion & execution |

## Setup

### 1. Install dependencies

```bash
pip install openai rich python-dotenv
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

## Free Models Used

- `meta-llama/llama-3.3-70b-instruct:free`
- `google/gemma-3-27b-it:free`
- `deepseek/deepseek-r1:free`
- `mistralai/mistral-7b-instruct:free`
- `qwen/qwen2.5-72b-instruct:free`

## Requirements

- Python 3.8+
- Ubuntu / Linux recommended
- OpenRouter API key(s)
