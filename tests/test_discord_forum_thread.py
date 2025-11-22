"""
Test Discord forum thread functionality - ensures messages are posted to the same thread
"""

import os
import sys
import time
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.notifiers.discord_notifier import DiscordNotifier


def test_forum_thread_posting():
    """Test posting multiple messages to the same forum thread"""

    load_dotenv()

    # Configuration for forum channel
    config = {
        'enabled': True,
        'rich_embeds': True,
        'webhook_env': 'DISCORD_AI_TRENDS_WEBHOOK',
        'thread_name': 'Test Thread - Multiple Messages',  # This creates a thread in forum
        'summary': {
            'enabled': False,
            'webhook_env': 'DISCORD_AI_TRENDS_SUMMARY_WEBHOOK'
        }
    }

    notifier = DiscordNotifier(config)

    if not notifier.webhook_url:
        print("❌ Discord webhook not configured. Set DISCORD_AI_TRENDS_WEBHOOK in .env")
        return False

    print("🧪 Testing forum thread posting...")
    print(f"Webhook URL: {notifier.webhook_url[:50]}...")
    print(f"Thread name: {notifier.thread_name}")
    print()

    # Test 1: Send header message (creates thread)
    print("📝 Test 1: Sending header message (creates thread)...")
    header = "# Test Report - Forum Thread\n\nThis is a test of the forum thread functionality."
    success, thread_id = notifier._send_message(header)

    if not success:
        print("❌ Failed to send header message")
        return False

    if thread_id:
        print(f"✅ Header sent successfully. Thread ID: {thread_id}")
    else:
        print("⚠️  Header sent, but no thread_id received (might be regular channel, not forum)")

    time.sleep(2)

    # Test 2: Send follow-up messages to the same thread
    print("\n📝 Test 2: Sending follow-up messages to the same thread...")

    messages = [
        "**Message 1:** This should appear as a reply in the thread.",
        "**Message 2:** This is another reply in the same thread.",
        "**Message 3:** Final message in the thread."
    ]

    for i, msg in enumerate(messages, 1):
        print(f"   Sending message {i}/3...")
        success, _ = notifier._send_message(msg, thread_id=thread_id)

        if not success:
            print(f"   ❌ Failed to send message {i}")
            return False

        print(f"   ✅ Message {i} sent")
        time.sleep(1)

    print("\n✅ All messages sent successfully!")

    if thread_id:
        print(f"\n📌 Check your Discord forum channel for a thread named '{config['thread_name']}'")
        print(f"   Thread ID: {thread_id}")
        print("   All messages should appear in the SAME thread (not separate threads)")
    else:
        print("\n⚠️  Messages sent to regular channel (not a forum)")

    return True


def test_rich_embeds_in_forum():
    """Test sending rich embeds to a forum thread"""

    load_dotenv()

    config = {
        'enabled': True,
        'rich_embeds': True,
        'webhook_env': 'DISCORD_AI_TRENDS_WEBHOOK',
        'thread_name': 'Test Thread - Rich Embeds',
        'summary': {
            'enabled': False,
            'webhook_env': 'DISCORD_AI_TRENDS_SUMMARY_WEBHOOK'
        }
    }

    notifier = DiscordNotifier(config)

    if not notifier.webhook_url:
        print("❌ Discord webhook not configured")
        return False

    print("\n" + "="*60)
    print("🧪 Testing rich embeds in forum thread...")
    print()

    # Create test content items
    test_contents = [
        {
            'title': 'Test Article 1',
            'translated_title': 'Article de Test 1',
            'hook': 'This is a test article with an interesting hook',
            'insights': '**Key Points:**\n- Point 1\n- Point 2\n- Point 3',
            'category': 'Large Language Models',
            'relevance_score': 9,
            'metadata': {
                'source': 'reddit',
                'author': 'test_user',
                'subreddit': 'artificial',
                'url': 'https://reddit.com/test1',
                'permalink': 'https://reddit.com/r/artificial/test1'
            }
        },
        {
            'title': 'Test Video 1',
            'translated_title': 'Vidéo de Test 1',
            'hook': 'An amazing AI breakthrough explained',
            'insights': '**Main Takeaways:**\n- Breakthrough in AI\n- New architecture\n- Performance gains',
            'category': 'AI Research Papers',
            'relevance_score': 8,
            'metadata': {
                'source': 'youtube',
                'channel_title': 'AI Channel',
                'video_id': 'dQw4w9WgXcQ',
                'url': 'https://youtube.com/watch?v=dQw4w9WgXcQ'
            }
        }
    ]

    print("📝 Sending rich report with embeds...")
    success = notifier.send_rich_report(test_contents, mention_role="")

    if success:
        print("✅ Rich report sent successfully!")
        print(f"\n📌 Check your Discord forum for thread '{config['thread_name']}'")
        print("   The header and all embeds should be in the SAME thread")
    else:
        print("❌ Failed to send rich report")

    return success


if __name__ == "__main__":
    print("=" * 60)
    print("Discord Forum Thread Test")
    print("=" * 60)
    print()
    print("This test verifies that messages are posted to the same thread")
    print("in Discord forum channels, rather than creating separate threads.")
    print()

    # Run tests
    test1_success = test_forum_thread_posting()

    if test1_success:
        time.sleep(3)
        test2_success = test_rich_embeds_in_forum()
    else:
        test2_success = False

    print("\n" + "=" * 60)
    print("Test Summary:")
    print(f"  Basic messaging: {'✅ PASS' if test1_success else '❌ FAIL'}")
    print(f"  Rich embeds: {'✅ PASS' if test2_success else '❌ FAIL'}")
    print("=" * 60)

    sys.exit(0 if (test1_success and test2_success) else 1)
