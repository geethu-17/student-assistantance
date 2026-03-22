#!/usr/bin/env python3
"""
Quick Telegram Webhook Setup for Local Testing
Sets up webhook for local development using ngrok or direct localhost
"""

import os
import json
import urllib.request
import urllib.error
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def setup_local_webhook():
    """Set up webhook for local testing"""

    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    if not bot_token:
        print("❌ TELEGRAM_BOT_TOKEN not found in .env")
        return False

    print("🔧 Setting up Telegram webhook for local testing...")
    print("\nChoose your setup method:")
    print("1. Use ngrok tunnel (recommended for testing)")
    print("2. Use localhost directly (limited functionality)")
    print("3. Enter custom webhook URL")

    choice = input("\nEnter choice (1-3): ").strip()

    if choice == "1":
        print("\n📋 To use ngrok:")
        print("1. Download ngrok from https://ngrok.com/download")
        print("2. Run: ngrok http 5000")
        print("3. Copy the HTTPS URL (e.g., https://abc123.ngrok.io)")
        print("4. Run this script again and choose option 3")
        return False

    elif choice == "2":
        webhook_url = "http://localhost:5000/api/integrations/telegram/webhook"
        print(f"⚠️  Using localhost URL: {webhook_url}")
        print("Note: This won't work for external Telegram messages")

    elif choice == "3":
        webhook_url = input("Enter your webhook URL: ").strip()
        if not webhook_url:
            print("❌ No URL provided")
            return False
    else:
        print("❌ Invalid choice")
        return False

    # Set the webhook
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
            print(f"🔒 Using webhook secret token")

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode('utf-8'),
            method='POST'
        )
        req.add_header('Content-Type', 'application/json')

        print(f"📡 Setting webhook to: {webhook_url}")

        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode('utf-8'))

        if data.get("ok"):
            print("✅ Webhook set successfully!")

            # Verify the webhook
            info_url = f"https://api.telegram.org/bot{bot_token}/getWebhookInfo"
            with urllib.request.urlopen(info_url, timeout=10) as info_response:
                info_data = json.loads(info_response.read().decode('utf-8'))

            if info_data.get("ok"):
                webhook_info = info_data.get("result", {})
                print(f"📊 Webhook Info:")
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

def test_webhook():
    """Test the webhook with a sample message"""

    print("\n🧪 Testing webhook with sample message...")

    # Sample Telegram message payload
    test_payload = {
        "message": {
            "chat": {"id": 123456789, "type": "private"},
            "from": {"id": 123456789, "first_name": "Test", "username": "testuser"},
            "text": "Hello! I need help with admissions",
            "date": 1640995200
        }
    }

    try:
        url = "http://localhost:5000/api/integrations/telegram/webhook"
        req = urllib.request.Request(
            url,
            data=json.dumps(test_payload).encode('utf-8'),
            method='POST'
        )
        req.add_header('Content-Type', 'application/json')

        with urllib.request.urlopen(req, timeout=10) as response:
            response_data = json.loads(response.read().decode('utf-8'))

        if response_data.get("ok"):
            print("✅ Webhook test successful!")
            print(f"🤖 Bot responded to test message")
            return True
        else:
            print("⚠️  Webhook responded but may have issues")
            return False

    except Exception as e:
        print(f"❌ Webhook test failed: {str(e)}")
        print("💡 Make sure your backend server is running (python app.py)")
        return False

def main():
    print("🚀 Quick Telegram Webhook Setup")
    print("=" * 50)

    # Setup webhook
    success = setup_local_webhook()

    if success:
        print("\n" + "=" * 50)
        print("🎉 WEBHOOK SETUP COMPLETE!")
        print("=" * 50)

        # Test webhook if using localhost
        if "localhost" in str(success):
            test_webhook()

        print("\n📱 Next Steps:")
        print("1. Start your backend: python app.py")
        print("2. Send a message to your bot on Telegram")
        print("3. Check the backend logs for incoming messages")
        print("4. Test responses from the bot")

        print("\n🔗 Your bot username: @Student_Support_231FA04G24_bot")
        print("💬 Try sending: 'Hello' or 'admissions help'")

if __name__ == "__main__":
    main()