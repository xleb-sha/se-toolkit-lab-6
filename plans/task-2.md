# Task 2: The Documentation Agent

## Overview

This task extends the agent from Task 1 with two file system tools (`read_file`, `list_files`) and implements an agentic loop that allows the LLM to iteratively call tools before producing a final answer.

## Tool Schemas

### read_file

**Purpose:** Read contents of a file from the project repository.

**Parameters:**
- `path` (string): Relative path from project root (e.g., `wiki/git-workflow.md`)

**Returns:** File contents as string, or error message if file doesn't exist.

**Security:** 
- Resolve the path and verify it stays within project directory.
- Reject any path containing `../` traversal.
- Use `os.path.realpath()` to resolve symlinks and check the final path.

### list_files

**Purpose:** List files and directories at a given path.

**Parameters:**
- `path` (string): Relative directory path from project root (e.g., `wiki`)

**Returns:** Newline-separated listing of entries (files and directories).

**Security:**
- Same path validation as `read_file`.
- Only allow listing within project directory.

## Agentic Loop Implementation

```
1. Send user question + tool definitions to LLM
2. Parse LLM response:
   - If tool_calls present:
     a. Execute each tool call
     b. Append results as "tool" role messages
     c. Loop back to step 1 (max 10 iterations)
   - If no tool_calls (text response):
     a. Extract answer and source
     b. Output JSON and exit
3. If max iterations (10) reached, use whatever answer we have
```

### Message Structure

```python
messages = [
    {"role": "system", "content": SYSTEM_PROMPT},
    {"role": "user", "content": question}
]
# After each tool call iteration:
# Append {"role": "tool", "tool_call_id": "...", "content": result}
```

### Tool Call Tracking

Track all tool calls in a list for the output:
```python
tool_calls_log = []
# Each entry: {"tool": "read_file", "args": {"path": "..."}, "result": "..."}
```

## Path Security Strategy

1. **Project root detection:** Use `Path(__file__).parent.parent` to get project root.
2. **Path resolution:** Combine project root + relative path, then use `resolve()` to get absolute path.
3. **Validation:** Check that resolved path starts with project root.
4. **Reject:** Any path with `..` components or paths that escape project directory.

## System Prompt Strategy

The system prompt will instruct the LLM to:
1. Use `list_files` to discover wiki files when needed.
2. Use `read_file` to read specific files and find answers.
3. Always include a `source` field with file path + section anchor (e.g., `wiki/git-workflow.md#resolving-merge-conflicts`).
4. Call tools iteratively until confident about the answer.
5. Return final answer as a text message (not a tool call) when done.

## Output Format

```json
{
  "answer": "string",
  "source": "wiki/file.md#section",
  "tool_calls": [
    {"tool": "list_files", "args": {"path": "wiki"}, "result": "..."},
    {"tool": "read_file", "args": {"path": "wiki/file.md"}, "result": "..."}
  ]
}
```

## Testing Strategy

1. **Test 1:** "How do you resolve a merge conflict?"
   - Expect: `read_file` in tool_calls
   - Expect: `wiki/git-workflow.md` in source

2. **Test 2:** "What files are in the wiki?"
   - Expect: `list_files` in tool_calls

## Error Handling

- File not found → return error message as tool result
- Permission denied → return error message
- Path traversal attempt → reject and return error
- LLM API errors → exit with error message to stderr
