#!/usr/bin/env python3
import os
from dotenv import load_dotenv
import urllib.request
import json

# Load env
load_dotenv('.env.docker.secret')
lms_key = os.getenv('LMS_API_KEY')
api_base = os.getenv('AGENT_API_BASE_URL', 'http://localhost:42002')
print(f'LMS_API_KEY: {lms_key}')
print(f'AGENT_API_BASE_URL: {api_base}')

# Test HTTP request directly
req = urllib.request.Request(
    f'{api_base}/items/',
    headers={
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {lms_key}'
    },
    method='GET'
)
try:
    with urllib.request.urlopen(req, timeout=10) as resp:
        print(f'Status: {resp.status}')
        body = resp.read().decode()
        print(f'Body: {body[:200]}')
except Exception as e:
    print(f'Error: {e}')
