"""
Regression tests for Task 1: Call an LLM from Code.

Tests verify that agent.py:
1. Outputs valid JSON
2. Contains required 'answer' and 'tool_calls' fields
"""

import json
import subprocess
import sys
from pathlib import Path


def test_agent_output_structure():
    """Test that agent.py outputs valid JSON with answer and tool_calls."""
    agent_path = Path(__file__).parent.parent / "agent.py"
    
    if not agent_path.exists():
        raise FileNotFoundError(f"agent.py not found at {agent_path}")
    
    # Run agent with a simple test question
    test_question = "What is 2 + 2?"
    
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
    
    print(f"✓ Test passed. Answer: {data['answer'][:50]}...")


if __name__ == "__main__":
    test_agent_output_structure()
    print("All tests passed!")
