"""Test Discord webhook with forum channel support"""

import requests
import time
from datetime import datetime

# Test webhook URL pointing to a forum channel
FORUM_WEBHOOK_URL = "https://discord.com/api/webhooks/1441708680851755171/gPlbj5fCsX-B4sn85wX1nz08So2kWoc3BD5euPCLNWXmrdM0f_7Js66SCKl53gsng_1H"

def test_simple_message():
    """Test 1: Simple message without thread_name (should fail on forum)"""
    print("\n=== Test 1: Simple message (no thread_name) ===")
    payload = {
        "content": "Test message without thread_name"
    }

    response = requests.post(FORUM_WEBHOOK_URL, json=payload, timeout=10)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")

    return response.status_code in (200, 204)


def test_forum_thread_message():
    """Test 2: Message with thread_name (should work on forum)"""
    print("\n=== Test 2: Message with thread_name ===")

    # For forum channels, we need to specify thread_name
    current_time = datetime.now().strftime('%H:%M:%S')
    payload = {
        "content": "✅ Test message avec thread_name - cela devrait créer un nouveau thread !",
        "thread_name": f"🧪 Test SCRIBE - {current_time}"
    }

    response = requests.post(FORUM_WEBHOOK_URL, json=payload, timeout=10)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")

    return response.status_code in (200, 204)


def test_forum_rich_embed():
    """Test 3: Rich embed with thread_name"""
    print("\n=== Test 3: Rich embed in forum thread ===")

    current_time = datetime.now().strftime('%H:%M:%S')
    payload = {
        "thread_name": f"📊 Test Embed - {current_time}",
        "embeds": [{
            "title": "Test Rich Embed",
            "description": "Ceci est un test d'embed dans un canal forum avec thread_name",
            "color": 0x5865F2,  # Discord blurple
            "fields": [
                {
                    "name": "Field 1",
                    "value": "Value 1",
                    "inline": True
                },
                {
                    "name": "Field 2",
                    "value": "Value 2",
                    "inline": True
                }
            ],
            "footer": {
                "text": "SCRIBE Test"
            },
            "timestamp": datetime.utcnow().isoformat()
        }]
    }

    response = requests.post(FORUM_WEBHOOK_URL, json=payload, timeout=10)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")

    return response.status_code in (200, 204)


def test_forum_multiple_embeds():
    """Test 4: Multiple embeds in a forum thread"""
    print("\n=== Test 4: Multiple embeds in forum thread ===")

    current_time = datetime.now().strftime('%H:%M:%S')
    payload = {
        "thread_name": f"📚 Test Multiple Embeds - {current_time}",
        "embeds": [
            {
                "title": "Embed 1",
                "description": "Premier embed dans le thread",
                "color": 0x57F287,  # Green
                "timestamp": datetime.utcnow().isoformat()
            },
            {
                "title": "Embed 2",
                "description": "Deuxième embed dans le thread",
                "color": 0xED4245,  # Red
                "timestamp": datetime.utcnow().isoformat()
            }
        ]
    }

    response = requests.post(FORUM_WEBHOOK_URL, json=payload, timeout=10)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")

    return response.status_code in (200, 204)


def test_forum_with_content_and_embeds():
    """Test 5: Content + embeds in forum thread"""
    print("\n=== Test 5: Content + Embeds in forum thread ===")

    current_time = datetime.now().strftime('%H:%M:%S')
    payload = {
        "thread_name": f"💬 Test Complet - {current_time}",
        "content": "**Voici un message avec du contenu ET des embeds**",
        "embeds": [{
            "title": "Détails supplémentaires",
            "description": "Les embeds peuvent compléter le message principal",
            "color": 0x9B59B6,  # Purple
            "image": {
                "url": "https://picsum.photos/400/300"
            },
            "timestamp": datetime.utcnow().isoformat()
        }]
    }

    response = requests.post(FORUM_WEBHOOK_URL, json=payload, timeout=10)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")

    return response.status_code in (200, 204)


if __name__ == "__main__":
    print("=" * 70)
    print("DISCORD FORUM CHANNEL WEBHOOK TESTS")
    print("=" * 70)

    results = []

    # Test 1: Without thread_name (expected to fail on forum)
    results.append(("Simple message (no thread_name)", test_simple_message()))
    time.sleep(2)

    # Test 2: With thread_name (should work)
    results.append(("Message with thread_name", test_forum_thread_message()))
    time.sleep(2)

    # Test 3: Rich embed
    results.append(("Rich embed", test_forum_rich_embed()))
    time.sleep(2)

    # Test 4: Multiple embeds
    results.append(("Multiple embeds", test_forum_multiple_embeds()))
    time.sleep(2)

    # Test 5: Content + embeds
    results.append(("Content + Embeds", test_forum_with_content_and_embeds()))

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {test_name}")

    passed = sum(1 for _, success in results if success)
    total = len(results)
    print(f"\nTotal: {passed}/{total} tests passed")
