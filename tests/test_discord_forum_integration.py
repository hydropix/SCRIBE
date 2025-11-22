"""Test Discord notifier with forum channel webhook"""

import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.notifiers.discord_notifier import DiscordNotifier

# Test webhook URL pointing to a forum channel
FORUM_WEBHOOK_URL = "https://discord.com/api/webhooks/1441708680851755171/gPlbj5fCsX-B4sn85wX1nz08So2kWoc3BD5euPCLNWXmrdM0f_7Js66SCKl53gsng_1H"


def test_simple_message_with_thread():
    """Test 1: Simple message with thread_name"""
    print("\n=== Test 1: Simple message with thread_name ===")

    # Configure Discord notifier for forum channel
    config = {
        "webhook_env": "DISCORD_FORUM_TEST_WEBHOOK",
        "rich_embeds": True,
        "thread_name": f"🧪 Test Message - {datetime.now().strftime('%H:%M:%S')}"
    }

    # Set the webhook URL in environment
    os.environ["DISCORD_FORUM_TEST_WEBHOOK"] = FORUM_WEBHOOK_URL

    notifier = DiscordNotifier(config)

    # Send a simple message
    success = notifier._send_message("✅ Test réussi avec thread_name automatique!")

    print(f"Result: {'SUCCESS' if success else 'FAILED'}")
    return success


def test_rich_embeds_with_thread():
    """Test 2: Rich embeds with thread_name"""
    print("\n=== Test 2: Rich embeds with thread_name ===")

    config = {
        "webhook_env": "DISCORD_FORUM_TEST_WEBHOOK",
        "rich_embeds": True,
        "thread_name": f"📊 Test Embeds - {datetime.now().strftime('%H:%M:%S')}"
    }

    os.environ["DISCORD_FORUM_TEST_WEBHOOK"] = FORUM_WEBHOOK_URL

    notifier = DiscordNotifier(config)

    # Create sample content items (simulating SCRIBE analysis results)
    relevant_contents = [
        {
            "title": "Test Article 1",
            "translated_title": "Premier article de test",
            "hook": "Ceci est un teaser accrocheur pour l'article",
            "insights": "**Insight 1:** Point important\n**Insight 2:** Autre observation",
            "category": "Large Language Models",
            "relevance_score": 9,
            "metadata": {
                "source": "reddit",
                "author": "test_user",
                "subreddit": "artificial",
                "url": "https://reddit.com/r/artificial/test",
                "permalink": "https://reddit.com/r/artificial/test"
            }
        },
        {
            "title": "Test Video",
            "translated_title": "Vidéo de test YouTube",
            "hook": "Une vidéo fascinante sur l'IA",
            "insights": "**Point clé:** Excellente démonstration\n**Application:** Cas d'usage intéressant",
            "category": "Computer Vision",
            "relevance_score": 8,
            "metadata": {
                "source": "youtube",
                "channel_title": "AI Research Channel",
                "video_id": "dQw4w9WgXcQ",
                "url": "https://youtube.com/watch?v=dQw4w9WgXcQ"
            }
        }
    ]

    # Send rich report
    success = notifier.send_rich_report(relevant_contents)

    print(f"Result: {'SUCCESS' if success else 'FAILED'}")
    return success


def test_without_thread_name():
    """Test 3: Without thread_name (should fail on forum)"""
    print("\n=== Test 3: Without thread_name (should fail on forum) ===")

    config = {
        "webhook_env": "DISCORD_FORUM_TEST_WEBHOOK",
        "rich_embeds": True,
        # NO thread_name - should fail
    }

    os.environ["DISCORD_FORUM_TEST_WEBHOOK"] = FORUM_WEBHOOK_URL

    notifier = DiscordNotifier(config)

    # This should fail with forum channel
    success = notifier._send_message("❌ Ce message devrait échouer sans thread_name")

    print(f"Result: {'FAILED as expected' if not success else 'UNEXPECTED SUCCESS'}")
    return not success  # We expect this to fail


def test_dynamic_thread_name():
    """Test 4: Dynamic thread_name with date"""
    print("\n=== Test 4: Dynamic thread_name with date ===")

    current_date = datetime.now().strftime('%d %B %Y - %H:%M')

    config = {
        "webhook_env": "DISCORD_FORUM_TEST_WEBHOOK",
        "rich_embeds": True,
        "thread_name": f"📅 Rapport AI Trends - {current_date}"
    }

    os.environ["DISCORD_FORUM_TEST_WEBHOOK"] = FORUM_WEBHOOK_URL

    notifier = DiscordNotifier(config)

    # Send a report-style message
    message = """**# AI TRENDS & INNOVATIONS**

---

## Résumé du jour

Voici les insights les plus importants du jour :

1. ✅ Nouvelle avancée en LLM
2. ✅ Amélioration de Computer Vision
3. ✅ Breakthrough en Robotique

---

*Rapport généré par SCRIBE*
"""

    success = notifier._send_message(message)

    print(f"Result: {'SUCCESS' if success else 'FAILED'}")
    return success


if __name__ == "__main__":
    print("=" * 70)
    print("DISCORD FORUM CHANNEL INTEGRATION TESTS")
    print("=" * 70)

    results = []

    # Test 1: Simple message
    results.append(("Simple message with thread_name", test_simple_message_with_thread()))

    # Test 2: Rich embeds
    results.append(("Rich embeds with thread_name", test_rich_embeds_with_thread()))

    # Test 3: Without thread_name (should fail)
    results.append(("Without thread_name (expected fail)", test_without_thread_name()))

    # Test 4: Dynamic thread name
    results.append(("Dynamic thread_name", test_dynamic_thread_name()))

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    for test_name, success in results:
        status = "PASS" if success else "FAIL"
        print(f"{status} - {test_name}")

    passed = sum(1 for _, success in results if success)
    total = len(results)
    print(f"\nTotal: {passed}/{total} tests passed")
