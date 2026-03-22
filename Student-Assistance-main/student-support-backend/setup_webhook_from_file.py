#!/usr/bin/env python3
"""
Set Telegram Webhook from ngrok URL
Reads the webhook URL from webhook_url.txt and sets it up
"""

import os
import json
import urllib.request
from dotenv import load_dotenv

load_dotenv()

def setup_webhook_from_file():
    # Read webhook URL from file
    webhook_url_file = "webhook_url.txt"

    if not os.path.exists(webhook_url_file):
        print("❌ webhook_url.txt not found!")
        print("💡 Run setup_ngrok.ps1 first to generate the webhook URL")
        return False

    with open(webhook_url_file, 'r') as f:
        webhook_url = f.read().strip()

    if not webhook_url:
        print("❌ Webhook URL is empty!")
        return False

    print(f"🔗 Setting webhook to: {webhook_url}")

    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        print("❌ TELEGRAM_BOT_TOKEN not found in .env")
        return False

    try:
        url = f"https://api.telegram.org/bot{bot_token}/setWebhook"
        payload = {
            "url": webhook_url,
            "max_connections": 100,
            "allowed_updates": ["message", "edited_message"]
        }

        # Add secret token if available
        secret_token = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")
        if secret_token and secret_token != "your_secure_webhook_secret_here":
            payload["secret_token"] = secret_token
            print("🔒 Using webhook secret token")

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode('utf-8'),
            method='POST'
        )
        req.add_header('Content-Type', 'application/json')

        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode('utf-8'))

        if data.get("ok"):
            print("✅ Telegram webhook set successfully!")

            # Verify the webhook
            info_url = f"https://api.telegram.org/bot{bot_token}/getWebhookInfo"
            with urllib.request.urlopen(info_url, timeout=10) as info_response:
                info_data = json.loads(info_response.read().decode('utf-8'))

            if info_data.get("ok"):
                webhook_info = info_data.get("result", {})
                print("📊 Webhook Info:")
                print(f"   URL: {webhook_info.get('url', 'Not set')}")
                print(f"   Pending updates: {webhook_info.get('pending_update_count', 0)}")

            return True
        else:
            error_msg = data.get("description", "Unknown error")
            print(f"❌ Failed to set webhook: {error_msg}")
            return False

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 Setting up Telegram webhook from ngrok URL")
    print("=" * 50)

    success = setup_webhook_from_file()

    if success:
        print("\n" + "=" * 50)
        print("🎉 WEBHOOK SETUP COMPLETE!")
        print("=" * 50)
        print("\n📱 Ready to test!")
        print("1. Make sure ngrok is still running")
        print("2. Start your backend: python app.py")
        print("3. Send a message to @Student_Support_231FA04G24_bot")
        print("4. Check backend logs for incoming messages")
    else:
        print("\n❌ Webhook setup failed. Check the errors above.")