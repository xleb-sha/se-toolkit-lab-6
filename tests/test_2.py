"""
Regression tests for Task 2: The Documentation Agent.

Tests verify that agent.py:
1. Uses read_file tool for documentation questions
2. Uses list_files tool for directory listing questions
3. Returns proper source references
"""

import json
import subprocess
import sys
from pathlib import Path


def test_resolve_merge_conflict():
    """
    Test that agent uses read_file to answer questions about merge conflicts.
    
    Expected behavior:
    - Agent should call read_file to read wiki/git-workflow.md
    - Source field should reference wiki/git-workflow.md
    """
    agent_path = Path(__file__).parent.parent / "agent.py"

    if not agent_path.exists():
        raise FileNotFoundError(f"agent.py not found at {agent_path}")

    test_question = "How do you resolve a merge conflict?"

    result = subprocess.run(
        [sys.executable, str(agent_path), test_question],
        capture_output=True,
        text=True,
        timeout=60,
    )

    # Check exit code
    assert result.returncode == 0, (
        f"Agent exited with code {result.returncode}\n"
        f"Stderr: {result.stderr}"
    )

    # Check stdout is not empty
    assert result.stdout.strip(), "Agent produced no output"

    # Parse JSON
    try:
        data = json.loads(result.stdout.strip())
    except json.JSONDecodeError as e:
        raise AssertionError(f"Agent output is not valid JSON: {result.stdout[:200]}") from e

    # Check required fields
    assert "answer" in data, "Missing 'answer' field in output"
    assert isinstance(data["answer"], str), "'answer' field must be a string"

    assert "source" in data, "Missing 'source' field in output"
    assert isinstance(data["source"], str), "'source' field must be a string"

    assert "tool_calls" in data, "Missing 'tool_calls' field in output"
    assert isinstance(data["tool_calls"], list), "'tool_calls' field must be an array"

    # Check that read_file was called
    tools_used = [call["tool"] for call in data["tool_calls"]]
    assert "read_file" in tools_used, (
        f"Expected 'read_file' in tool_calls, got: {tools_used}"
    )

    # Check that source references wiki/git-workflow.md
    assert "wiki/git-workflow.md" in data["source"], (
        f"Expected 'wiki/git-workflow.md' in source, got: {data['source']}"
    )

    print(f"✓ Test passed. Answer: {data['answer'][:50]}...")
    print(f"  Source: {data['source']}")
    print(f"  Tools used: {tools_used}")


def test_list_wiki_files():
    """
    Test that agent uses list_files to answer questions about wiki contents.
    
    Expected behavior:
    - Agent should call list_files with path 'wiki'
    """
    agent_path = Path(__file__).parent.parent / "agent.py"

    if not agent_path.exists():
        raise FileNotFoundError(f"agent.py not found at {agent_path}")

    test_question = "What files are in the wiki?"

    result = subprocess.run(
        [sys.executable, str(agent_path), test_question],
        capture_output=True,
        text=True,
        timeout=60,
    )

    # Check exit code
    assert result.returncode == 0, (
        f"Agent exited with code {result.returncode}\n"
        f"Stderr: {result.stderr}"
    )

    # Check stdout is not empty
    assert result.stdout.strip(), "Agent produced no output"

    # Parse JSON
    try:
        data = json.loads(result.stdout.strip())
    except json.JSONDecodeError as e:
        raise AssertionError(f"Agent output is not valid JSON: {result.stdout[:200]}") from e

    # Check required fields
    assert "answer" in data, "Missing 'answer' field in output"
    assert isinstance(data["answer"], str), "'answer' field must be a string"

    assert "tool_calls" in data, "Missing 'tool_calls' field in output"
    assert isinstance(data["tool_calls"], list), "'tool_calls' field must be an array"

    # Check that list_files was called
    tools_used = [call["tool"] for call in data["tool_calls"]]
    assert "list_files" in tools_used, (
        f"Expected 'list_files' in tool_calls, got: {tools_used}"
    )

    # Check that list_files was called with path 'wiki'
    list_files_calls = [
        call for call in data["tool_calls"]
        if call["tool"] == "list_files"
    ]
    wiki_paths = [
        call["args"].get("path") for call in list_files_calls
        if call["args"].get("path") == "wiki"
    ]
    assert len(wiki_paths) > 0, (
        f"Expected list_files to be called with path 'wiki', got: {[c['args'] for c in list_files_calls]}"
    )

    print(f"✓ Test passed. Answer: {data['answer'][:50]}...")
    print(f"  Tools used: {tools_used}")


if __name__ == "__main__":
    print("Running test_resolve_merge_conflict...")
    test_resolve_merge_conflict()
    print()
    
    print("Running test_list_wiki_files...")
    test_list_wiki_files()
    print()
    
    print("All Task 2 tests passed!")
