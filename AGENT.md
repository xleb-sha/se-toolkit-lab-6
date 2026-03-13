# Agent Architecture

## Overview

The agent is a Python CLI program (`agent.py`) that processes user questions by querying a Large Language Model (LLM) and returns structured JSON responses.

## Task 1: Basic LLM Integration

### Architecture

```
User Input (CLI arg) → Agent → LLM API → JSON Output
```

### Components

- **CLI Interface**: Parses command-line arguments to extract the user question
- **Environment Configuration**: Loads LLM credentials and settings from `.env.agent.secret`
- **LLM Client**: Uses OpenAI-compatible API to communicate with Qwen Code API
- **Response Formatter**: Structures the LLM response into JSON format with `answer` and `tool_calls` fields

### Data Flow

1. User runs: `uv run agent.py "What does REST stand for?"`
2. Agent loads environment variables (`LLM_API_KEY`, `LLM_API_BASE`, `LLM_MODEL`)
3. Agent sends question to LLM via chat completions API
4. Agent receives response and formats as JSON: `{"answer": "...", "tool_calls": []}`
5. Agent prints JSON to stdout and exits with code 0

### Error Handling

- Invalid arguments: Print usage to stderr, exit code 1
- Missing environment variables: Print error to stderr, exit code 1
- API errors: Print error to stderr, exit code 1
- Timeout: 60 seconds maximum response time

### Dependencies

- `openai`: For LLM API communication
- `python-dotenv`: For environment variable loading

### Configuration

Environment variables in `.env.agent.secret`:
- `LLM_API_KEY`: API key for Qwen Code API
- `LLM_API_BASE`: Base URL for OpenAI-compatible endpoint
- `LLM_MODEL`: Model name (e.g., `qwen3-coder-plus`)