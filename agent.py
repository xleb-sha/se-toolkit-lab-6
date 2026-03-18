#!/usr/bin/env python3
"""
System Agent CLI with file system and API tools.

This agent can:
- Read files and list directories (wiki, source code)
- Query the backend LMS API for live data
It implements an agentic loop: LLM decides which tool to call, code executes it, feeds result back.
"""

import sys
import json
import os
import urllib.request
import urllib.error
import urllib.parse
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

# Maximum number of tool calls per question
MAX_TOOL_CALLS = 10


def get_project_root() -> Path:
    """Get the project root directory (parent of agent.py)."""
    return Path(__file__).parent.resolve()


def validate_path(relative_path: str, project_root: Path) -> Path:
    """
    Validate that a relative path stays within project directory.

    Args:
        relative_path: Path relative to project root
        project_root: Project root directory

    Returns:
        Resolved absolute path

    Raises:
        ValueError: If path escapes project directory
    """
    # Check for obvious traversal attempts
    if ".." in relative_path:
        raise ValueError(f"Path traversal not allowed: {relative_path}")

    # Combine and resolve
    full_path = (project_root / relative_path).resolve()

    # Ensure the resolved path is within project root
    if not str(full_path).startswith(str(project_root)):
        raise ValueError(f"Path escapes project directory: {relative_path}")

    return full_path


def read_file(path: str) -> str:
    """
    Read a file from the project repository.

    Args:
        path: Relative path from project root

    Returns:
        File contents as string, or error message
    """
    try:
        project_root = get_project_root()
        full_path = validate_path(path, project_root)

        if not full_path.exists():
            return f"Error: File not found: {path}"

        if not full_path.is_file():
            return f"Error: Not a file: {path}"

        return full_path.read_text(encoding="utf-8")

    except ValueError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Error reading file: {e}"


def list_files(path: str) -> str:
    """
    List files and directories at a given path.

    Args:
        path: Relative directory path from project root

    Returns:
        Newline-separated listing of entries
    """
    try:
        project_root = get_project_root()
        full_path = validate_path(path, project_root)

        if not full_path.exists():
            return f"Error: Directory not found: {path}"

        if not full_path.is_dir():
            return f"Error: Not a directory: {path}"

        entries = []
        for entry in sorted(full_path.iterdir()):
            prefix = "[DIR] " if entry.is_dir() else ""
            entries.append(f"{prefix}{entry.name}")

        return "\n".join(entries)

    except ValueError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Error listing directory: {e}"


def query_api(method: str, path: str, body: str = None) -> str:
    """
    Query the backend LMS API.

    Args:
        method: HTTP method (GET, POST, PUT, DELETE)
        path: API endpoint path (e.g., /items/, /analytics/completion-rate)
        body: Optional JSON request body for POST/PUT requests

    Returns:
        JSON string with status_code and body
    """
    try:
        # Get LMS API key from environment (already loaded or injected by autochecker)
        # Only load from file if not already set
        load_dotenv('.env.docker.secret', override=False)

        lms_api_key = os.getenv('LMS_API_KEY')
        api_base_url = os.getenv('AGENT_API_BASE_URL', 'http://localhost:42002')

        if not lms_api_key:
            return json.dumps({
                "status_code": 401,
                "body": {"error": "LMS_API_KEY not configured"}
            })

        # Build full URL
        # Handle query parameters in path
        if '?' in path:
            full_url = f"{api_base_url}{path}"
        else:
            full_url = f"{api_base_url}{path}"

        # Prepare request
        # Backend uses Bearer token authentication (see backend/app/auth.py)
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {lms_api_key}"
        }

        data = None
        if body:
            data = body.encode('utf-8')

        # Create request
        req = urllib.request.Request(
            full_url,
            data=data,
            headers=headers,
            method=method.upper()
        )

        # Execute request
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                response_body = response.read().decode('utf-8')
                status_code = response.status
                try:
                    parsed_body = json.loads(response_body)
                except json.JSONDecodeError:
                    parsed_body = response_body

        except urllib.error.HTTPError as e:
            status_code = e.code
            error_body = e.read().decode('utf-8') if e.fp else ""
            try:
                parsed_body = json.loads(error_body)
            except json.JSONDecodeError:
                parsed_body = error_body

        # Return as JSON string
        return json.dumps({
            "status_code": status_code,
            "body": parsed_body
        })

    except Exception as e:
        return json.dumps({
            "status_code": 0,
            "body": {"error": f"Request failed: {str(e)}"}
        })


# Tool definitions for LLM function calling
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file from the project repository. Use this to read documentation files (wiki/*.md) or source code to find answers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path from project root (e.g., 'wiki/git-workflow.md' or 'backend/app/main.py')"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files and directories at a given path. Use this to discover what files exist in a directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative directory path from project root (e.g., 'wiki', 'backend/app')"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_api",
            "description": "Query the backend LMS API to get live data from the database. Use this for questions about items count, statistics, analytics, or any data stored in the system. The API requires authentication.",
            "parameters": {
                "type": "object",
                "properties": {
                    "method": {
                        "type": "string",
                        "description": "HTTP method: GET, POST, PUT, DELETE",
                        "enum": ["GET", "POST", "PUT", "DELETE"]
                    },
                    "path": {
                        "type": "string",
                        "description": "API endpoint path (e.g., '/items/', '/analytics/completion-rate', '/pipeline/status')"
                    },
                    "body": {
                        "type": "string",
                        "description": "Optional JSON request body for POST/PUT requests (e.g., '{\"key\": \"value\"}')"
                    }
                },
                "required": ["method", "path"]
            }
        }
    }
]

# Map function names to actual Python functions
TOOL_FUNCTIONS = {
    "read_file": read_file,
    "list_files": list_files,
    "query_api": query_api
}

SYSTEM_PROMPT = """You are a system assistant that answers questions by reading files, querying the backend API, or exploring the project structure.

You have three tools available:
1. list_files - to discover what files exist in a directory
2. read_file - to read the contents of a specific file (wiki docs or source code)
3. query_api - to query the backend LMS API for live data from the database

When answering questions, choose the right tool:
- For wiki/documentation questions (e.g., "What is the git workflow?") → use list_files and read_file on wiki/*.md files
- For live data questions (e.g., "How many items are in the database?") → use query_api with GET /items/
- For source code questions (e.g., "What framework does the backend use?") → use read_file on backend/*.py files
- For analytics questions (e.g., "What is the completion rate?") → use query_api with /analytics/* endpoints

When using query_api:
- Use GET method for fetching data
- Common endpoints: /items/, /analytics/scores, /analytics/pass-rates, /analytics/completion-rate, /pipeline/status
- Include query parameters when needed (e.g., /analytics/completion-rate?lab=lab-01)

When you find the answer, respond with a text message (not a tool call) that includes:
- The answer to the question
- For wiki/source questions: a source reference like "wiki/git-workflow.md#section" or "backend/app/main.py"
- For API questions: you don't need a source field

Think step by step - you can call multiple tools before giving your final answer.
Do not make up information. Only answer based on what you read in the files or get from the API."""


def execute_tool_call(tool_call, project_root: Path) -> str:
    """
    Execute a single tool call and return the result.

    Args:
        tool_call: Tool call object from LLM response
        project_root: Project root directory

    Returns:
        Tool execution result as string
    """
    function_name = tool_call.function.name
    args = json.loads(tool_call.function.arguments)

    if function_name not in TOOL_FUNCTIONS:
        return f"Error: Unknown tool: {function_name}"

    func = TOOL_FUNCTIONS[function_name]

    # Execute the tool
    result = func(**args)

    return result


def main():
    # Load environment variables from files only if not already set
    # This allows the autochecker to inject its own values
    load_dotenv('.env.agent.secret', override=False)
    # LMS_API_KEY will be loaded from .env.docker.secret by query_api when needed

    # Check command line arguments
    if len(sys.argv) != 2:
        print("Usage: uv run agent.py \"question\"", file=sys.stderr)
        sys.exit(1)

    question = sys.argv[1]
    project_root = get_project_root()

    # Get environment variables
    api_key = os.getenv('LLM_API_KEY')
    api_base = os.getenv('LLM_API_BASE')
    model = os.getenv('LLM_MODEL')

    if not all([api_key, api_base, model]):
        print("Error: Missing required environment variables (LLM_API_KEY, LLM_API_BASE, LLM_MODEL)", file=sys.stderr)
        sys.exit(1)

    try:
        # Initialize OpenAI client
        client = OpenAI(
            api_key=api_key,
            base_url=api_base,
            timeout=60.0  # 60 second timeout
        )

        # Initialize messages with system prompt and user question
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question}
        ]

        # Track all tool calls for output
        tool_calls_log = []

        # Agentic loop
        iteration = 0
        final_answer = None

        while iteration < MAX_TOOL_CALLS:
            iteration += 1

            # Call LLM with current messages and tool definitions
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                tools=TOOLS
            )

            # Get the response message
            response_message = response.choices[0].message

            # Check if LLM wants to call tools
            tool_calls = response_message.tool_calls

            if not tool_calls:
                # No tool calls - this is the final answer
                final_answer = response_message.content
                break

            # Append the assistant's message with tool calls
            messages.append(response_message)

            # Execute each tool call
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                args = json.loads(tool_call.function.arguments)

                # Execute the tool
                result = execute_tool_call(tool_call, project_root)

                # Log the tool call for output
                tool_calls_log.append({
                    "tool": function_name,
                    "args": args,
                    "result": result
                })

                # Append tool result as a "tool" role message
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result
                })

        # If we hit max iterations, use whatever we have
        if iteration >= MAX_TOOL_CALLS and final_answer is None:
            final_answer = "I reached the maximum number of tool calls. Based on the information gathered, I'll provide the best answer I can."

        # Extract source from the final answer if possible
        # Look for wiki file references in the answer
        source = ""
        if final_answer:
            # Try to find a wiki file reference in the answer
            import re
            wiki_match = re.search(r'wiki/[\w\-/]+\.md(?:#[\w\-]+)?', final_answer)
            if wiki_match:
                source = wiki_match.group(0)
            else:
                # Also check for source code references
                code_match = re.search(r'(?:backend|tests|agent\.py)(?:/[\w\-\.]+)+', final_answer)
                if code_match:
                    source = code_match.group(0)

        # Format output
        output = {
            "answer": final_answer,
            "source": source,
            "tool_calls": tool_calls_log
        }

        # Print JSON to stdout
        print(json.dumps(output, indent=2))

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
