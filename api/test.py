#!/usr/bin/env python3
"""
Simple test handler to verify Vercel Python runtime is working
This should work even if main app has issues
"""
import sys
import os
import json
from datetime import datetime

def handler(event, context):
    """
    Minimal handler for testing
    """
    print("🔧 Test handler invoked!", file=sys.stdout, flush=True)
    print(f"Event: {json.dumps(event, indent=2)}", file=sys.stdout, flush=True)
    
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps({
            'status': 'ok',
            'message': 'Test handler is working!',
            'timestamp': datetime.utcnow().isoformat(),
            'python_version': sys.version,
            'cwd': os.getcwd(),
            'sys_path': sys.path[:3]  # First 3 paths
        })
    }

