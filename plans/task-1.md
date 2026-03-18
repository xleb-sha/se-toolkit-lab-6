# Task 1 Plan: Call an LLM from Code

## LLM Provider and Model

**Provider:** Qwen Code API
- OpenAI-compatible endpoint
- 1000 free requests per day
- Works from Russia, no credit card required

**Model:** `qwen3-coder-plus`
- Strong tool calling capabilities
- Recommended default for this lab

## Configuration

Environment variables in `.env.agent.secret`:
- `LLM_API_KEY` — API key from Qwen Code deployment
- `LLM_API_BASE` — Base URL (e.g., `http://<vm-ip>:<port>/v1`)
- `LLM_MODEL` — `qwen3-coder-plus`

## Agent Structure

### Components

1. **CLI Interface**
   - Parse command-line argument (user question)
   - Validate input (exactly 1 argument required)
   - Exit with code 1 on invalid usage

2. **Environment Loader**
   - Load `.env.agent.secret` using `python-dotenv`
   - Validate all required variables are present
   - Exit with code 1 if missing

3. **LLM Client**
   - Initialize OpenAI client with custom base URL
   - Set 60-second timeout
   - Send user question via `chat.completions.create()`
   - Handle API errors gracefully

4. **Response Formatter**
   - Extract content from LLM response
   - Build JSON object with required fields:
     - `answer`: string from LLM
     - `tool_calls`: empty array (for Task 1)
   - Output valid JSON to stdout

### Data Flow

```
Command line → Parse args → Load env → Create client → Call LLM → Format JSON → stdout
```

### Error Handling

| Error | Action |
|-------|--------|
| Wrong number of arguments | Print usage to stderr, exit 1 |
| Missing env vars | Print error to stderr, exit 1 |
| API timeout | Print error to stderr, exit 1 |
| API error | Print error to stderr, exit 1 |

### Output Format

```json
{"answer": "Representational State Transfer.", "tool_calls": []}
```

### Dependencies

- `openai` — LLM API client
- `python-dotenv` — Environment variable loading

## Testing Strategy

Create one regression test that:
1. Runs `agent.py` as subprocess with a test question
2. Parses stdout as JSON
3. Verifies `answer` field exists and is a string
4. Verifies `tool_calls` field exists and is an array

## Implementation Steps

1. ✅ Read `.env.agent.example` and create `.env.agent.secret`
2. ✅ Implement `agent.py` with CLI parsing and LLM call
3. ✅ Ensure all debug output goes to stderr
4. ✅ Create regression test in `tests/`
5. ✅ Write documentation in `AGENT.md`
