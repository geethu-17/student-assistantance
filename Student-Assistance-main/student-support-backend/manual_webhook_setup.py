#!/usr/bin/env python3
"""
Manual Webhook Setup for Telegram
Allows you to enter ngrok URL manually and set up the webhook
"""

import os
import json
import urllib.request
from dotenv import load_dotenv

load_dotenv()

def manual_webhook_setup():
    print("🚀 Manual Telegram Webhook Setup")
    print("=" * 50)

    # Get ngrok URL from user
    print("Enter your ngrok HTTPS URL (e.g., https://abc123.ngrok.io):")
    ngrok_url = input("ngrok URL: ").strip()

    if not ngrok_url:
        print("❌ No URL provided")
        return False

    # Ensure it ends with /api/integrations/telegram/webhook
    if not ngrok_url.endswith('/api/integrations/telegram/webhook'):
        if ngrok_url.endswith('/'):
            webhook_url = ngrok_url + 'api/integrations/telegram/webhook'
        else:
            webhook_url = ngrok_url + '/api/integrations/telegram/webhook'
    else:
        webhook_url = ngrok_url

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
    success = manual_webhook_setup()

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