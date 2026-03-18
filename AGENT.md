# Agent Architecture

## Overview

The agent is a Python CLI program (`agent.py`) that processes user questions by querying a Large Language Model (LLM) with access to file system tools. It implements an **agentic loop** where the LLM can iteratively call tools (`read_file`, `list_files`) to gather information before producing a final answer.

## Task 2: The Documentation Agent

### Architecture

```
User Question → Agent → LLM (with tools) → Tool Calls? → Execute Tools → Feed Back → LLM → Final Answer
```

### Components

- **CLI Interface**: Parses command-line arguments to extract the user question
- **Environment Configuration**: Loads LLM credentials from `.env.agent.secret`
- **Tool System**: Two file system tools (`read_file`, `list_files`) with path security
- **Agentic Loop**: Iteratively executes tool calls and feeds results back to LLM
- **Response Formatter**: Structures output as JSON with `answer`, `source`, and `tool_calls` fields

### Tools

#### read_file

Reads the contents of a file from the project repository.

**Parameters:**
- `path` (string): Relative path from project root (e.g., `wiki/git-workflow.md`)

**Returns:** File contents as string, or error message if file doesn't exist.

**Security:**
- Validates that the path does not contain `..` traversal
- Resolves the full path and verifies it stays within project directory
- Returns error message for invalid paths

#### list_files

Lists files and directories at a given path.

**Parameters:**
- `path` (string): Relative directory path from project root (e.g., `wiki`)

**Returns:** Newline-separated listing of entries (directories prefixed with `[DIR]`).

**Security:**
- Same path validation as `read_file`
- Only allows listing within project directory

### Agentic Loop

The agentic loop enables multi-step reasoning:

1. **Initialize messages** with system prompt and user question
2. **Call LLM** with tool definitions
3. **Check response:**
   - If `tool_calls` present:
     - Execute each tool
     - Append results as `tool` role messages
     - Loop back to step 2 (max 10 iterations)
   - If no tool calls (text response):
     - This is the final answer
     - Extract answer and source
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

1. Use `list_files` to discover wiki files
2. Use `read_file` to read specific files and find answers
3. Always include a source reference (file path + section anchor)
4. Think step by step - call multiple tools if needed
5. Return final answer as a text message (not a tool call)

### Data Flow

```
1. User runs: uv run agent.py "How do you resolve a merge conflict?"
2. Agent loads environment variables
3. Agent sends question + system prompt + tool definitions to LLM
4. LLM responds with tool_calls (e.g., list_files wiki/)
5. Agent executes tool, appends result to messages
6. Agent sends updated messages back to LLM
7. LLM responds with more tool_calls or final answer
8. Agent extracts answer and source, outputs JSON
```

### Output Format

```json
{
  "answer": "Edit the conflicting file, choose which changes to keep, then stage and commit.",
  "source": "wiki/git-workflow.md#resolving-merge-conflicts",
  "tool_calls": [
    {
      "tool": "list_files",
      "args": {"path": "wiki"},
      "result": "git-workflow.md\n..."
    },
    {
      "tool": "read_file",
      "args": {"path": "wiki/git-workflow.md"},
      "result": "..."
    }
  ]
}
```

### Output Fields

| Field | Type | Description |
|-------|------|-------------|
| `answer` | string | The LLM's answer to the question |
| `source` | string | Wiki section reference (e.g., `wiki/git-workflow.md#section`) |
| `tool_calls` | array | All tool calls made during execution |

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

### LLM Provider

**Provider:** Qwen Code API
- OpenAI-compatible endpoint
- Works with function calling

**Model:** `qwen3-coder-plus`

### Error Handling

| Error | Action |
|-------|--------|
| Invalid arguments | Print usage to stderr, exit code 1 |
| Missing environment variables | Print error to stderr, exit code 1 |
| File not found | Return error as tool result |
| Path traversal attempt | Return error as tool result |
| API errors | Print error to stderr, exit code 1 |
| Timeout | 60 seconds maximum response time |
| Max tool calls (10) | Use whatever answer is available |

### Dependencies

- `openai`: For LLM API communication
- `python-dotenv`: For environment variable loading

### Configuration

Environment variables in `.env.agent.secret`:
- `LLM_API_KEY`: API key for Qwen Code API
- `LLM_API_BASE`: Base URL for OpenAI-compatible endpoint
- `LLM_MODEL`: Model name (e.g., `qwen3-coder-plus`)

### Running the Agent

```bash
# Basic usage
uv run agent.py "How do you resolve a merge conflict?"

# Expected output
{
  "answer": "...",
  "source": "wiki/git-workflow.md#...",
  "tool_calls": [...]
}
```

### Testing

Run regression tests:

```bash
uv run pytest tests/test_1.py tests/test_task_2.py -v
```

Tests verify:
1. Agent exits with code 0
2. Output is valid JSON
3. Required fields (`answer`, `source`, `tool_calls`) exist
4. Expected tools are called for specific questions

### Future Extensions (Task 3)

- Add more tools (API query, code search, etc.)
- Expand system prompt with domain knowledge
- Improve source extraction logic
- Add caching for repeated file reads
