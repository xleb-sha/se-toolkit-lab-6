#!/usr/bin/env python3
"""
Simple CLI agent that takes a question, sends it to Qwen Code API, and returns JSON answer.
"""

import sys
import json
import os
from dotenv import load_dotenv
from openai import OpenAI

def main():
    # Load environment variables
    load_dotenv('.env.agent.secret')
    
    # Check command line arguments
    if len(sys.argv) != 2:
        print("Usage: uv run agent.py \"question\"", file=sys.stderr)
        sys.exit(1)
    
    question = sys.argv[1]
    
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
            timeout=60.0  # 60 second timeout as required
        )
        
        # Call the LLM
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": question}]
        )
        
        # Extract answer
        answer = response.choices[0].message.content
        
        # Format output
        output = {
            "answer": answer,
            "tool_calls": []
        }
        
        # Print JSON to stdout
        print(json.dumps(output))
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
