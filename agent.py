#!/usr/bin/env python3
"""
Documentation Agent CLI with file system tools.

This agent can read files and list directories to answer questions based on project documentation.
It implements an agentic loop: LLM decides which tool to call, code executes it, feeds result back.
"""

import sys
import json
import os
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


# Tool definitions for LLM function calling
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file from the project repository. Use this to read documentation files to find answers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path from project root (e.g., 'wiki/git-workflow.md')"
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
                        "description": "Relative directory path from project root (e.g., 'wiki')"
                    }
                },
                "required": ["path"]
            }
        }
    }
]

# Map function names to actual Python functions
TOOL_FUNCTIONS = {
    "read_file": read_file,
    "list_files": list_files
}

SYSTEM_PROMPT = """You are a documentation assistant that answers questions by reading files from the project wiki.

You have two tools available:
1. list_files - to discover what files exist in a directory
2. read_file - to read the contents of a specific file

When answering questions:
1. First use list_files to discover relevant wiki files (e.g., list the "wiki" directory)
2. Then use read_file to read specific files and find the answer
3. Always include a source reference in your final answer (file path + section anchor if applicable)
4. Think step by step - you can call multiple tools before giving your final answer

When you have found the answer, respond with a text message (not a tool call) that includes:
- The answer to the question
- A source reference like "wiki/git-workflow.md#resolving-merge-conflicts"

Do not make up information. Only answer based on what you read in the files."""


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
    # Load environment variables
    load_dotenv('.env.agent.secret')

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
        print("Error: Missing required environment variables in .env.agent.secret", file=sys.stderr)
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
