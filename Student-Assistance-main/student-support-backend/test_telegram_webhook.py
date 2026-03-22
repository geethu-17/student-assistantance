#!/usr/bin/env python3
"""
Test Telegram Webhook with Mock Data
Tests the webhook endpoint with sample Telegram message payload
"""

import json
import urllib.request
import urllib.error

def test_telegram_webhook():
    """Test Telegram webhook with mock message data"""

    # Mock Telegram message payload
    mock_payload = {
        "message": {
            "chat": {
                "id": 123456789,
                "type": "private"
            },
            "from": {
                "id": 123456789,
                "first_name": "Test",
                "username": "testuser"
            },
            "text": "Hello, I need help with admissions",
            "date": 1640995200
        }
    }

    print("🧪 Testing Telegram Webhook with Mock Data")
    print("=" * 50)
    print(f"📨 Mock Message: '{mock_payload['message']['text']}'")
    print(f"👤 From User: {mock_payload['message']['from']['first_name']} (@{mock_payload['message']['from']['username']})")
    print(f"💬 Chat ID: {mock_payload['message']['chat']['id']}")

    try:
        url = "http://localhost:5000/api/integrations/telegram/webhook"
        req = urllib.request.Request(
            url,
            data=json.dumps(mock_payload).encode('utf-8'),
            method='POST'
        )
        req.add_header('Content-Type', 'application/json')

        print("\n📡 Sending request to webhook...")

        with urllib.request.urlopen(req, timeout=10) as response:
            response_data = json.loads(response.read().decode('utf-8'))

        print("✅ Webhook responded successfully!")
        print(f"📊 Response: {json.dumps(response_data, indent=2)}")

        if response_data.get("ok") and response_data.get("processed", 0) > 0:
            print("🎉 Message processing successful!")
            return {"status": "success", "response": response_data}
        else:
            print("⚠️  Message processed but may have issues")
            return {"status": "warning", "response": response_data}

    except urllib.error.HTTPError as e:
        try:
            error_data = json.loads(e.read().decode('utf-8'))
        except:
            error_data = {"error": str(e)}

        print(f"❌ HTTP Error {e.code}: {error_data}")
        return {"status": "error", "error": error_data}

    except urllib.error.URLError as e:
        print(f"❌ Connection Error: {str(e)}")
        print("💡 Make sure the backend server is running on http://localhost:5000")
        return {"status": "error", "error": str(e)}

    except Exception as e:
        print(f"❌ Unexpected Error: {str(e)}")
        return {"status": "error", "error": str(e)}

def main():
    print("🚀 Telegram Webhook Test")
    print("=" * 50)

    result = test_telegram_webhook()

    print("\n" + "=" * 50)
    print("📊 TEST RESULTS")
    print("=" * 50)

    if result["status"] == "success":
        print("✅ Webhook Test: PASSED")
        print("🎉 Telegram integration is fully functional!")
    elif result["status"] == "warning":
        print("⚠️  Webhook Test: PARTIAL SUCCESS")
        print("📝 Check response details above")
    else:
        print("❌ Webhook Test: FAILED")
        print("🔧 Fix the issues above before proceeding")

if __name__ == "__main__":
    main()