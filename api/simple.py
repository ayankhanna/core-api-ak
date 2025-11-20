"""
Absolutely minimal handler to test Vercel Python runtime
"""

def handler(event, context):
    """Minimal Vercel handler"""
    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': '{"status":"ok","message":"Simple handler works!"}'
    }

