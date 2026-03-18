# Agent Architecture

## Overview

The agent is a Python CLI program (`agent.py`) that processes user questions by querying a Large Language Model (LLM) with access to file system tools and a backend API. It implements an **agentic loop** where the LLM can iteratively call tools (`read_file`, `list_files`, `query_api`) to gather information before producing a final answer.

## Task 3: The System Agent

### Architecture

```
User Question → Agent → LLM (with 3 tools) → Tool Calls? → Execute Tools → Feed Back → LLM → Final Answer
```

### Components

- **CLI Interface**: Parses command-line arguments to extract the user question
- **Environment Configuration**: Loads LLM credentials from `.env.agent.secret` and backend API key from `.env.docker.secret`
- **Tool System**: Three tools available:
  - `read_file` — read wiki documentation or source code
  - `list_files` — discover files in directories
  - `query_api` — query the backend LMS API for live data
- **Agentic Loop**: Iteratively executes tool calls and feeds results back to LLM (max 10 iterations)
- **Response Formatter**: Structures output as JSON with `answer`, `source` (optional), and `tool_calls` fields

### Tools

#### read_file

Reads the contents of a file from the project repository.

**Parameters:**
- `path` (string): Relative path from project root (e.g., `wiki/git-workflow.md` or `backend/app/main.py`)

**Returns:** File contents as string, or error message if file doesn't exist.

**Security:**
- Validates that the path does not contain `..` traversal
- Resolves the full path and verifies it stays within project directory
- Returns error message for invalid paths

**Use cases:**
- Reading wiki documentation for conceptual questions
- Reading source code for implementation questions

#### list_files

Lists files and directories at a given path.

**Parameters:**
- `path` (string): Relative directory path from project root (e.g., `wiki`, `backend/app`)

**Returns:** Newline-separated listing of entries (directories prefixed with `[DIR]`).

**Security:**
- Same path validation as `read_file`
- Only allows listing within project directory

**Use cases:**
- Discovering available wiki files
- Exploring project structure

#### query_api

Queries the backend LMS API to get live data from the database.

**Parameters:**
- `method` (string): HTTP method (GET, POST, PUT, DELETE)
- `path` (string): API endpoint path (e.g., `/items/`, `/analytics/completion-rate`)
- `body` (string, optional): JSON request body for POST/PUT requests

**Returns:** JSON string with `status_code` and `body` fields.

**Authentication:**
- Uses `LMS_API_KEY` from `.env.docker.secret`
- Sends API key via `X-API-Key` header
- Handles 401/403 authentication errors gracefully

**Common endpoints:**
- `GET /items/` — list all items
- `GET /items/{id}` — get specific item
- `GET /analytics/scores?lab=lab-01` — score distribution
- `GET /analytics/pass-rates?lab=lab-01` — per-task pass rates
- `GET /analytics/completion-rate?lab=lab-01` — completion rate
- `GET /analytics/timeline?lab=lab-01` — submissions per day
- `GET /pipeline/status` — ETL pipeline status

**Use cases:**
- Counting items in the database
- Fetching analytics and statistics
- Checking pipeline status

### Tool Selection Strategy

The LLM decides which tool to use based on the question type:

| Question Type | Example | Tool to Use |
|--------------|---------|-------------|
| Wiki/Documentation | "What is the git workflow?" | `list_files` → `read_file` on wiki/*.md |
| Live Data | "How many items are in the database?" | `query_api` GET /items/ |
| Source Code | "What framework does the backend use?" | `read_file` on backend/app/main.py |
| Analytics | "What is the completion rate for lab-01?" | `query_api` GET /analytics/completion-rate?lab=lab-01 |

### Agentic Loop

The agentic loop enables multi-step reasoning:

1. **Initialize messages** with system prompt and user question
2. **Call LLM** with 3 tool definitions
3. **Check response:**
   - If `tool_calls` present:
     - Execute each tool
     - Append results as `tool` role messages
     - Loop back to step 2 (max 10 iterations)
   - If no tool calls (text response):
     - This is the final answer
     - Extract answer and source (if applicable)
     - Output JSON and exit
4. **Max iterations:** If 10 tool calls reached, use whatever answer is available

### Message Structure

```python
messages = [
    {"role": "system", "content": SYSTEM_PROMPT},
    {"role": "user", "content": question}
]

# After each tool call:
# Append assistant message with tool_calls
messages.append(response_message)

# After tool execution:
# Append tool result
messages.append({
    "role": "tool",
    "tool_call_id": tool_call.id,
    "content": result
})
```

### System Prompt Strategy

The system prompt instructs the LLM to:

1. **Choose the right tool** based on question type
2. **Use list_files first** to discover wiki files when needed
3. **Use read_file** to read specific files and find answers
4. **Use query_api** for live data questions with appropriate endpoints
5. **Include source references** for wiki/source questions (optional for API questions)
6. **Think step by step** — call multiple tools if needed
7. **Return final answer** as a text message (not a tool call)

### Data Flow

```
1. User runs: uv run agent.py "How many items are in the database?"
2. Agent loads environment variables (LLM_API_KEY, LMS_API_KEY)
3. Agent sends question + system prompt + 3 tool definitions to LLM
4. LLM responds with tool_calls (e.g., query_api GET /items/)
5. Agent executes tool, appends result to messages
6. Agent sends updated messages back to LLM
7. LLM counts items and returns final answer
8. Agent outputs JSON with answer and tool_calls
```

### Output Format

```json
{
  "answer": "There are 120 items in the database.",
  "source": "",  // optional for API questions
  "tool_calls": [
    {
      "tool": "query_api",
      "args": {"method": "GET", "path": "/items/"},
      "result": "{\"status_code\": 200, \"body\": [...]}"
    }
  ]
}
```

### Output Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `answer` | string | Yes | The LLM's answer to the question |
| `source` | string | No | Wiki/source reference (e.g., `wiki/git-workflow.md#section`) |
| `tool_calls` | array | Yes | All tool calls made during execution |

### Environment Variables

| Variable | Purpose | Source |
|----------|---------|--------|
| `LLM_API_KEY` | LLM provider API key | `.env.agent.secret` |
| `LLM_API_BASE` | LLM API endpoint URL | `.env.agent.secret` |
| `LLM_MODEL` | Model name | `.env.agent.secret` |
| `LMS_API_KEY` | Backend API key for `query_api` | `.env.docker.secret` |
| `AGENT_API_BASE_URL` | Base URL for backend API (optional) | Default: `http://localhost:42002` |

**Important:** The autochecker injects its own values. Never hardcode these values.

### Path Security

Security is enforced through:

1. **Path validation function:** `validate_path()` checks for `..` traversal
2. **Path resolution:** Uses `Path.resolve()` to get absolute path
3. **Prefix check:** Verifies resolved path starts with project root
4. **Error handling:** Returns error messages instead of raising exceptions

```python
def validate_path(relative_path: str, project_root: Path) -> Path:
    if ".." in relative_path:
        raise ValueError(f"Path traversal not allowed: {relative_path}")
    
    full_path = (project_root / relative_path).resolve()
    
    if not str(full_path).startswith(str(project_root)):
        raise ValueError(f"Path escapes project directory: {relative_path}")
    
    return full_path
```

### API Authentication

The `query_api` tool authenticates with the backend using an API key:

```python
headers = {
    "Content-Type": "application/json",
    "X-API-Key": lms_api_key
}
```

The backend verifies the key using `app/auth.py::verify_api_key()`.

### LLM Provider

**Provider:** Qwen Code API
- OpenAI-compatible endpoint
- Supports function calling

**Model:** `qwen3-coder-plus`

### Error Handling

| Error | Action |
|-------|--------|
| Invalid arguments | Print usage to stderr, exit code 1 |
| Missing environment variables | Print error to stderr, exit code 1 |
| File not found | Return error as tool result |
| Path traversal attempt | Return error as tool result |
| API authentication error | Return 401 status in response |
| API connection error | Return error message in response |
| LLM API errors | Print error to stderr, exit code 1 |
| Timeout | 60 seconds maximum response time |
| Max tool calls (10) | Use whatever answer is available |

### Dependencies

- `openai`: For LLM API communication
- `python-dotenv`: For environment variable loading
- `urllib.request`: For HTTP requests (built-in)

### Running the Agent

```bash
# Basic usage
uv run agent.py "How many items are in the database?"

# Expected output
{
  "answer": "There are 120 items...",
  "source": "",
  "tool_calls": [...]
}
```

### Testing

Run regression tests:

```bash
uv run pytest tests/test_1.py tests/test_task_2.py tests/test_task_3.py -v
```

Run the evaluation benchmark:

```bash
uv run run_eval.py
```

### Lessons Learned

1. **Tool descriptions matter:** The LLM relies on clear tool descriptions to decide which tool to use. Vague descriptions lead to wrong tool choices.

2. **API endpoint discovery:** The LLM needs to know available API endpoints. Including common endpoints in the system prompt helps.

3. **Error handling is crucial:** API calls can fail for many reasons (auth, network, invalid path). Graceful error handling allows the LLM to recover.

4. **Source extraction:** For API questions, the `source` field is optional. The agent only populates it for wiki/source code references.

5. **Iteration limit:** The 10-iteration limit prevents infinite loops but may truncate complex multi-step reasoning.

### Final Eval Score

(To be updated after passing the benchmark)
