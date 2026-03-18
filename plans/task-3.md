# Task 3: The System Agent

## Overview

This task extends the agent from Task 2 with a new tool `query_api` to query the backend LMS API. The agent must now decide between three types of tools:
- `list_files` / `read_file` — for wiki documentation
- `query_api` — for live data from the backend
- `read_file` — for reading source code

## Tool Schema: query_api

**Purpose:** Call the backend LMS API to fetch live data.

**Parameters:**
- `method` (string): HTTP method (GET, POST, PUT, DELETE)
- `path` (string): API endpoint path (e.g., `/items/`, `/analytics/completion-rate`)
- `body` (string, optional): JSON request body for POST/PUT requests

**Returns:** JSON string with `status_code` and `body` fields.

**Authentication:**
- Use `LMS_API_KEY` from `.env.docker.secret`
- Send as `X-API-Key` header (or Bearer token, depending on backend implementation)

**Environment Variables:**
- `LMS_API_KEY` — backend API key for authentication
- `AGENT_API_BASE_URL` — base URL for the API (default: `http://localhost:42002`)

## Authentication Strategy

The backend uses API key authentication via `app/auth.py`. The `query_api` tool must:

1. Read `LMS_API_KEY` from environment (via `.env.docker.secret`)
2. Include the API key in the request header
3. Handle authentication errors (401, 403)

```python
headers = {"X-API-Key": lms_api_key}  # or Authorization: Bearer <key>
```

## System Prompt Strategy

The system prompt must guide the LLM to choose the right tool:

1. **Wiki questions** (e.g., "What is the git workflow?") → use `list_files` + `read_file`
2. **Data questions** (e.g., "How many items in the database?") → use `query_api`
3. **Code questions** (e.g., "What framework does the backend use?") → use `read_file` on source code

Example prompt guidance:
- "If the question asks about live data, statistics, or database contents, use `query_api`"
- "If the question asks about documentation or wiki content, use `list_files` and `read_file`"
- "If the question asks about source code implementation, use `read_file`"

## Environment Variables

| Variable | Purpose | Source |
|----------|---------|--------|
| `LLM_API_KEY` | LLM provider API key | `.env.agent.secret` |
| `LLM_API_BASE` | LLM API endpoint URL | `.env.agent.secret` |
| `LLM_MODEL` | Model name | `.env.agent.secret` |
| `LMS_API_KEY` | Backend API key for `query_api` auth | `.env.docker.secret` |
| `AGENT_API_BASE_URL` | Base URL for `query_api` (optional) | Default: `http://localhost:42002` |

**Important:** The autochecker injects its own values. Never hardcode these values.

## Agentic Loop Updates

The agentic loop remains the same, but now with 3 tools:

```
1. Send question + 3 tool definitions to LLM
2. LLM decides which tool(s) to call
3. Execute tool calls, feed results back
4. Repeat until final answer (max 10 iterations)
```

## Output Format

```json
{
  "answer": "There are 120 items in the database.",
  "source": "",  // optional for system questions
  "tool_calls": [
    {"tool": "query_api", "args": {"method": "GET", "path": "/items/"}, "result": "..."}
  ]
}
```

Note: `source` is now **optional** — system questions may not have a wiki source.

## Implementation Steps

1. **Add `query_api` function** in `agent.py`:
   - Read `LMS_API_KEY` and `AGENT_API_BASE_URL` from environment
   - Use `requests` or `urllib` to make HTTP calls
   - Include API key in headers
   - Return JSON response with status_code and body

2. **Add tool schema** for LLM function calling:
   - Define `query_api` schema with `method`, `path`, `body` parameters
   - Register in `TOOLS` list

3. **Update system prompt**:
   - Explain when to use each tool
   - Provide examples of wiki vs API vs code questions

4. **Test with benchmark**:
   - Run `uv run run_eval.py`
   - Iterate on failures

## Initial Benchmark Score

**Status:** Backend running locally on port 42001.

To run the benchmark:
1. Start the backend: `docker compose up -d`
2. Ensure `.env.docker.secret` has `LMS_API_KEY=1234`
3. Set `AGENT_API_BASE_URL=http://localhost:42001` in `.env`
4. Run: `uv run run_eval.py`

**First Run Result:** Cannot test without valid LLM API key. The agent code is syntactically correct and `query_api` tool works when tested directly.

## Iteration Strategy

When tests fail:

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| Agent doesn't call `query_api` for data questions | Tool description unclear | Improve schema description |
| `query_api` returns 401 | Missing/wrong API key | Check `LMS_API_KEY` loading |
| `query_api` returns connection error | Wrong base URL | Check `AGENT_API_BASE_URL` |
| Agent loops infinitely | LLM can't find answer | Add max iterations, improve prompt |
| Answer doesn't match expected keywords | Phrasing issue | Adjust system prompt |

## Lessons Learned

1. **Authentication matters:** The backend uses Bearer token authentication (`Authorization: Bearer <key>`), not `X-API-Key` header. Had to check `backend/app/auth.py` to understand the correct scheme.

2. **Docker networking:** Caddy reverse proxy needs containers on the same Docker network. Direct API access via `localhost:42001` works for local testing.

3. **Environment variable separation:** `LMS_API_KEY` (backend auth) and `LLM_API_KEY` (LLM provider) are completely different keys from different files. Easy to confuse them.

4. **Tool descriptions are critical:** The LLM relies on clear tool descriptions to choose the right tool. Vague descriptions lead to wrong tool choices.

5. **Default URL:** The default `AGENT_API_BASE_URL` should be `http://localhost:42002` (Caddy), but direct access via port 42001 (app) works better for local testing.

## Final Eval Score

**Status:** Cannot run full benchmark without valid LLM API key.

Local testing confirms:
- `query_api` tool works correctly (tested directly)
- Authentication with Bearer token works
- All environment variables are read from config files
- Agent syntax is valid (py_compile passes)

To complete: Need valid `LLM_API_KEY` in `.env.agent.secret` to run `uv run run_eval.py`.
