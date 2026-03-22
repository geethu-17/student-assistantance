#!/usr/bin/env python3
"""
Set Telegram Webhook to Localhost for Testing
"""

import os
import json
import urllib.request
from dotenv import load_dotenv

load_dotenv()

def set_localhost_webhook():
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        print("❌ Bot token not found")
        return

    webhook_url = "http://localhost:5000/api/integrations/telegram/webhook"

    print(f"🔧 Setting webhook to: {webhook_url}")

    try:
        url = f"https://api.telegram.org/bot{bot_token}/setWebhook"
        payload = {"url": webhook_url}

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode('utf-8'),
            method='POST'
        )
        req.add_header('Content-Type', 'application/json')

        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))

        if data.get("ok"):
            print("✅ Localhost webhook set!")
            print("⚠️  Note: External messages won't work, only for local testing")
        else:
            print(f"❌ Error: {data.get('description')}")

    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    set_localhost_webhook()