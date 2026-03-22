#!/usr/bin/env python3
"""
Telegram Bot Integration Verification Script
Tests if the Telegram bot token is valid and can communicate with Telegram API
"""

import os
import json
import urllib.request
import urllib.error
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_telegram_bot():
    """Test Telegram bot token validity"""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")

    if not bot_token:
        return {"status": "error", "message": "TELEGRAM_BOT_TOKEN not found in .env"}

    print("🔍 Testing Telegram Bot Token...")
    print(f"Token: {bot_token[:20]}...")

    # Test 1: Get bot information
    try:
        url = f"https://api.telegram.org/bot{bot_token}/getMe"
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))

        if data.get("ok"):
            bot_info = data.get("result", {})
            print("✅ Bot authentication successful!")
            print(f"🤖 Bot Name: {bot_info.get('first_name', 'Unknown')}")
            print(f"👤 Username: @{bot_info.get('username', 'Unknown')}")
            print(f"🆔 Bot ID: {bot_info.get('id', 'Unknown')}")

            return {
                "status": "success",
                "bot_info": bot_info,
                "message": "Telegram bot token is valid and authenticated"
            }
        else:
            error_description = data.get("description", "Unknown error")
            print(f"❌ Bot authentication failed: {error_description}")
            return {
                "status": "error",
                "message": f"Telegram API error: {error_description}"
            }

    except urllib.error.HTTPError as e:
        try:
            error_data = json.loads(e.read().decode('utf-8'))
            error_msg = error_data.get("description", str(e))
        except:
            error_msg = str(e)

        print(f"❌ HTTP Error: {error_msg}")
        return {
            "status": "error",
            "message": f"HTTP Error: {error_msg}"
        }

    except Exception as e:
        print(f"❌ Connection Error: {str(e)}")
        return {
            "status": "error",
            "message": f"Connection error: {str(e)}"
        }

def test_webhook_endpoint():
    """Test if the webhook endpoint is accessible"""
    print("\n🔍 Testing Webhook Endpoint...")

    try:
        # Test webhook verification (GET request)
        url = "http://localhost:5000/api/integrations/telegram/webhook"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as response:
            print("✅ Webhook endpoint is accessible")
            return {"status": "success", "message": "Webhook endpoint accessible"}

    except urllib.error.HTTPError as e:
        if e.code == 403:
            print("⚠️  Webhook endpoint accessible but requires proper verification token")
            return {"status": "warning", "message": "Webhook requires verification token"}
        else:
            print(f"❌ Webhook endpoint error: {e.code}")
            return {"status": "error", "message": f"HTTP {e.code}"}

    except Exception as e:
        print(f"❌ Cannot connect to webhook: {str(e)}")
        print("💡 Make sure the backend server is running on http://localhost:5000")
        return {"status": "error", "message": "Backend server not running"}

def main():
    print("🚀 Telegram Integration Verification")
    print("=" * 50)

    # Test bot token
    bot_result = test_telegram_bot()

    # Test webhook (only if backend might be running)
    webhook_result = test_webhook_endpoint()

    print("\n" + "=" * 50)
    print("📊 VERIFICATION SUMMARY")
    print("=" * 50)

    if bot_result["status"] == "success":
        print("✅ Telegram Bot Token: VALID")
        print(f"   Bot: {bot_result['bot_info'].get('first_name')} (@{bot_result['bot_info'].get('username')})")
    else:
        print("❌ Telegram Bot Token: INVALID")
        print(f"   Error: {bot_result['message']}")

    if webhook_result["status"] == "success":
        print("✅ Webhook Endpoint: ACCESSIBLE")
    elif webhook_result["status"] == "warning":
        print("⚠️  Webhook Endpoint: REQUIRES TOKEN")
    else:
        print("❌ Webhook Endpoint: NOT ACCESSIBLE")
        print("   (Backend server may not be running)")

    print("\n" + "=" * 50)
    if bot_result["status"] == "success":
        print("🎉 Telegram integration is READY!")
        print("\nNext steps:")
        print("1. Set webhook URL in Telegram: https://api.telegram.org/bot<TOKEN>/setWebhook?url=<YOUR_WEBHOOK_URL>")
        print("2. Test with actual Telegram messages")
        print("3. Add TELEGRAM_WEBHOOK_SECRET to .env for security")
    else:
        print("❌ Telegram integration needs fixing")

if __name__ == "__main__":
    main()