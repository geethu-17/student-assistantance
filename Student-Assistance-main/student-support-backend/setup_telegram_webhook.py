#!/usr/bin/env python3
"""
Telegram Webhook Setup Script
Helps set up the webhook URL for your Telegram bot
"""

import os
import json
import urllib.request
import urllib.error
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def set_telegram_webhook(webhook_url=None):
    """Set the webhook URL for the Telegram bot"""

    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")

    if not bot_token:
        print("❌ TELEGRAM_BOT_TOKEN not found in .env")
        return False

    if not webhook_url:
        # Try to detect if running on a server or localhost
        webhook_url = input("Enter your webhook URL (e.g., https://yourdomain.com/api/integrations/telegram/webhook): ").strip()

        if not webhook_url:
            print("❌ No webhook URL provided")
            return False

    print(f"🔧 Setting webhook URL: {webhook_url}")
    print(f"🤖 Bot Token: {bot_token[:20]}...")

    try:
        url = f"https://api.telegram.org/bot{bot_token}/setWebhook"
        payload = {
            "url": webhook_url,
            "max_connections": 100,
            "allowed_updates": ["message", "edited_message"]
        }

        # Add secret token if available
        secret_token = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")
        if secret_token:
            payload["secret_token"] = secret_token
            print(f"🔒 Using webhook secret token: {secret_token[:10]}...")

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode('utf-8'),
            method='POST'
        )
        req.add_header('Content-Type', 'application/json')

        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode('utf-8'))

        if data.get("ok"):
            print("✅ Webhook set successfully!")
            print(f"🔗 URL: {webhook_url}")

            # Get webhook info to verify
            info_url = f"https://api.telegram.org/bot{bot_token}/getWebhookInfo"
            with urllib.request.urlopen(info_url, timeout=10) as info_response:
                info_data = json.loads(info_response.read().decode('utf-8'))

            if info_data.get("ok"):
                webhook_info = info_data.get("result", {})
                print(f"📊 Webhook Info:")
                print(f"   URL: {webhook_info.get('url', 'Not set')}")
                print(f"   Pending updates: {webhook_info.get('pending_update_count', 0)}")
                if webhook_info.get('last_error_message'):
                    print(f"   ⚠️  Last error: {webhook_info['last_error_message']}")

            return True
        else:
            error_msg = data.get("description", "Unknown error")
            print(f"❌ Failed to set webhook: {error_msg}")
            return False

    except urllib.error.HTTPError as e:
        try:
            error_data = json.loads(e.read().decode('utf-8'))
            error_msg = error_data.get("description", str(e))
        except:
            error_msg = str(e)
        print(f"❌ HTTP Error: {error_msg}")
        return False

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def delete_webhook():
    """Delete the current webhook"""

    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")

    if not bot_token:
        print("❌ TELEGRAM_BOT_TOKEN not found in .env")
        return False

    print("🗑️  Deleting webhook...")

    try:
        url = f"https://api.telegram.org/bot{bot_token}/deleteWebhook"
        req = urllib.request.Request(url, method='POST')
        req.add_header('Content-Type', 'application/json')

        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))

        if data.get("ok"):
            print("✅ Webhook deleted successfully!")
            return True
        else:
            error_msg = data.get("description", "Unknown error")
            print(f"❌ Failed to delete webhook: {error_msg}")
            return False

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def main():
    print("🚀 Telegram Webhook Setup")
    print("=" * 50)

    print("Choose an option:")
    print("1. Set webhook URL")
    print("2. Delete webhook")
    print("3. Check webhook info")

    choice = input("\nEnter choice (1-3): ").strip()

    if choice == "1":
        set_telegram_webhook()
    elif choice == "2":
        delete_webhook()
    elif choice == "3":
        # Check webhook info
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        if not bot_token:
            print("❌ TELEGRAM_BOT_TOKEN not found in .env")
            return

        try:
            url = f"https://api.telegram.org/bot{bot_token}/getWebhookInfo"
            with urllib.request.urlopen(url, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))

            if data.get("ok"):
                webhook_info = data.get("result", {})
                print("📊 Current Webhook Info:")
                print(f"   URL: {webhook_info.get('url', 'Not set')}")
                print(f"   Pending updates: {webhook_info.get('pending_update_count', 0)}")
                if webhook_info.get('last_error_message'):
                    print(f"   ⚠️  Last error: {webhook_info['last_error_message']}")
            else:
                print("❌ Failed to get webhook info")
        except Exception as e:
            print(f"❌ Error: {str(e)}")
    else:
        print("❌ Invalid choice")

if __name__ == "__main__":
    main()