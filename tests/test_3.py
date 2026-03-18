"""
Regression tests for Task 3: The System Agent.

Tests verify that agent.py:
1. Uses read_file for source code questions
2. Uses query_api for database/data questions
"""

import json
import subprocess
import sys
from pathlib import Path


def test_backend_framework():
    """
    Test that agent uses read_file to answer questions about backend framework.

    Expected behavior:
    - Agent should call read_file to read backend/app/main.py or similar
    - Source field should reference backend source code
    """
    agent_path = Path(__file__).parent.parent / "agent.py"

    if not agent_path.exists():
        raise FileNotFoundError(f"agent.py not found at {agent_path}")

    test_question = "What framework does the backend use?"

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

    # Check that read_file was called
    tools_used = [call["tool"] for call in data["tool_calls"]]
    assert "read_file" in tools_used, (
        f"Expected 'read_file' in tool_calls, got: {tools_used}"
    )

    # Check that source references backend code
    assert data.get("source") and "backend" in data["source"].lower(), (
        f"Expected 'backend' in source, got: {data.get('source')}"
    )

    print(f"✓ Test passed. Answer: {data['answer'][:100]}...")
    print(f"  Source: {data.get('source', 'N/A')}")
    print(f"  Tools used: {tools_used}")


def test_database_items_count():
    """
    Test that agent uses query_api to answer questions about database contents.

    Expected behavior:
    - Agent should call query_api with GET /items/
    - Answer should contain a number or count
    """
    agent_path = Path(__file__).parent.parent / "agent.py"

    if not agent_path.exists():
        raise FileNotFoundError(f"agent.py not found at {agent_path}")

    test_question = "How many items are in the database?"

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

    # Check that query_api was called
    tools_used = [call["tool"] for call in data["tool_calls"]]
    assert "query_api" in tools_used, (
        f"Expected 'query_api' in tool_calls, got: {tools_used}"
    )

    # Check that query_api was called with GET method and /items/ path
    query_api_calls = [
        call for call in data["tool_calls"]
        if call["tool"] == "query_api"
    ]
    items_calls = [
        call for call in query_api_calls
        if call["args"].get("method") == "GET" and "/items/" in call["args"].get("path", "")
    ]
    assert len(items_calls) > 0, (
        f"Expected query_api to be called with GET /items/, got: {[c['args'] for c in query_api_calls]}"
    )

    print(f"✓ Test passed. Answer: {data['answer'][:100]}...")
    print(f"  Tools used: {tools_used}")


if __name__ == "__main__":
    print("Running test_backend_framework...")
    test_backend_framework()
    print()

    print("Running test_database_items_count...")
    test_database_items_count()
    print()

    print("All Task 3 tests passed!")
