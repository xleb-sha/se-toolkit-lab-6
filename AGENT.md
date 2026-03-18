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

### LLM Provider

**Provider:** Qwen Code API
- OpenAI-compatible endpoint
- 1000 free requests per day
- Works from Russia, no credit card required

**Model:** `qwen3-coder-plus`
- Strong tool calling capabilities
- Recommended default for this lab

### Error Handling

| Error | Action |
|-------|--------|
| Invalid arguments | Print usage to stderr, exit code 1 |
| Missing environment variables | Print error to stderr, exit code 1 |
| API errors | Print error to stderr, exit code 1 |
| Timeout | 60 seconds maximum response time |

### Dependencies

- `openai`: For LLM API communication
- `python-dotenv`: For environment variable loading

### Configuration

Environment variables in `.env.agent.secret`:
- `LLM_API_KEY`: API key for Qwen Code API
- `LLM_API_BASE`: Base URL for OpenAI-compatible endpoint (e.g., `http://<vm-ip>:<port>/v1`)
- `LLM_MODEL`: Model name (e.g., `qwen3-coder-plus`)

### Running the Agent

```bash
# Basic usage
uv run agent.py "What does REST stand for?"

# Expected output
{"answer": "Representational State Transfer.", "tool_calls": []}
```

### Testing

Run the regression test:

```bash
uv run pytest tests/test_task_1.py -v
```

The test verifies:
1. Agent exits with code 0
2. Output is valid JSON
3. `answer` field exists and is a string
4. `tool_calls` field exists and is an array

### Future Extensions (Tasks 2-3)

- Add tools (file read, API query, etc.)
- Implement agentic loop for multi-step reasoning
- Expand system prompt with domain knowledge
- Add source tracking in output
