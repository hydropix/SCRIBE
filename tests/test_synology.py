#!/usr/bin/env python3
"""Test script for Synology Chat webhook integration"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.notifiers.synology_notifier import SynologyNotifier
from src.utils import load_env_variables


def test_synology_connection():
    """Test basic Synology Chat webhook connection"""
    print("=" * 60)
    print("SYNOLOGY CHAT WEBHOOK TEST")
    print("=" * 60)

    # Load environment variables
    print("\n1. Loading environment variables...")
    try:
        load_env_variables()
        print("   ✓ Environment variables loaded")
    except Exception as e:
        print(f"   ✗ Failed to load environment: {e}")
        return False

    # Check for webhook URL
    webhook_url = os.getenv('SYNOLOGY_AI_TRENDS_WEBHOOK')
    if not webhook_url:
        print("   ✗ SYNOLOGY_AI_TRENDS_WEBHOOK not configured in .env")
        print("   Please add your Synology Chat webhook URL to .env file")
        print("   Format: https://[DS_IP]:[PORT]/webapi/entry.cgi?api=SYNO.Chat.External&method=incoming&version=2&token=[TOKEN]")
        return False

    print(f"   ✓ Webhook URL found: {webhook_url[:50]}...")

    # Initialize notifier
    print("\n2. Initializing Synology Chat notifier...")
    config = {
        'webhook_env': 'SYNOLOGY_AI_TRENDS_WEBHOOK',
        'max_length': 1900
    }

    try:
        notifier = SynologyNotifier(config=config)
        print("   ✓ Notifier initialized")
    except Exception as e:
        print(f"   ✗ Failed to initialize notifier: {e}")
        return False

    # Test simple message
    print("\n3. Testing simple message...")
    try:
        success = notifier._send_message("🤖 SCRIBE Test Message\n\nThis is a test message from SCRIBE to verify Synology Chat webhook integration.")
        if success:
            print("   ✓ Simple message sent successfully!")
        else:
            print("   ✗ Failed to send simple message")
            return False
    except Exception as e:
        print(f"   ✗ Error sending simple message: {e}")
        return False

    # Test formatted message
    print("\n4. Testing formatted message...")
    test_content = {
        'title': 'Test Title: Synology Chat Integration',
        'translated_title': 'Integration de Synology Chat',
        'hook': 'This is a test hook/teaser for the content',
        'insights': '**Key Insights:**\n- Point 1: Synology Chat webhooks work!\n- Point 2: Messages are formatted correctly\n- Point 3: Integration successful',
        'category': 'AI Tools & Applications',
        'relevance_score': 9,
        'metadata': {
            'source': 'reddit',
            'author': 'test_user',
            'subreddit': 'artificial',
            'permalink': 'https://reddit.com/r/test/12345'
        }
    }

    try:
        message = notifier._create_content_message(test_content, 'AI Tools & Applications')
        success = notifier._send_message(message)
        if success:
            print("   ✓ Formatted message sent successfully!")
        else:
            print("   ✗ Failed to send formatted message")
            return False
    except Exception as e:
        print(f"   ✗ Error sending formatted message: {e}")
        return False

    # Test message splitting
    print("\n5. Testing message splitting (long message)...")
    long_message = "LONG MESSAGE TEST\n\n" + ("Lorem ipsum dolor sit amet. " * 200)
    try:
        chunks = notifier._split_message(long_message)
        print(f"   ✓ Message split into {len(chunks)} chunk(s)")

        if len(chunks) > 1:
            print(f"   Testing sending {len(chunks)} chunks...")
            for i, chunk in enumerate(chunks[:2], 1):  # Only send first 2 chunks to avoid spam
                success = notifier._send_message(chunk)
                if success:
                    print(f"   ✓ Chunk {i}/{min(2, len(chunks))} sent")
                else:
                    print(f"   ✗ Failed to send chunk {i}")
    except Exception as e:
        print(f"   ✗ Error testing message splitting: {e}")
        return False

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED ✓")
    print("=" * 60)
    print("\nYour Synology Chat webhook is working correctly!")
    print("You can now enable Synology notifications in your package settings.yaml")
    return True


def test_synology_summary():
    """Test Synology Chat summary webhook"""
    print("\n" + "=" * 60)
    print("SYNOLOGY CHAT SUMMARY WEBHOOK TEST")
    print("=" * 60)

    # Check for summary webhook URL
    summary_webhook_url = os.getenv('SYNOLOGY_AI_TRENDS_SUMMARY_WEBHOOK')
    if not summary_webhook_url:
        print("   ⚠ SYNOLOGY_AI_TRENDS_SUMMARY_WEBHOOK not configured")
        print("   Skipping summary webhook test")
        return True

    print(f"   ✓ Summary webhook URL found: {summary_webhook_url[:50]}...")

    # Initialize notifier with summary webhook
    config = {
        'webhook_env': 'SYNOLOGY_AI_TRENDS_WEBHOOK',
        'summary': {
            'enabled': True,
            'webhook_env': 'SYNOLOGY_AI_TRENDS_SUMMARY_WEBHOOK'
        }
    }

    try:
        notifier = SynologyNotifier(config=config)
        print("   ✓ Notifier initialized with summary webhook")
    except Exception as e:
        print(f"   ✗ Failed to initialize notifier: {e}")
        return False

    # Test summary message
    print("\n   Testing summary message...")
    summary_text = """📊 DAILY SUMMARY - TEST

This is a test daily summary for Synology Chat integration.

Key highlights:
- Integration working correctly
- Summary webhook configured
- Messages delivered successfully

Total insights: 5
Relevance threshold: 7/10"""

    try:
        success = notifier.send_summary(summary_text, mention="")
        if success:
            print("   ✓ Summary message sent successfully!")
        else:
            print("   ✗ Failed to send summary message")
            return False
    except Exception as e:
        print(f"   ✗ Error sending summary: {e}")
        return False

    print("\n   Summary webhook test completed ✓")
    return True


if __name__ == "__main__":
    print("\nSCRIBE - Synology Chat Integration Test\n")

    # Test main webhook
    success = test_synology_connection()

    # Test summary webhook if main webhook works
    if success:
        test_synology_summary()

    print("\n")
    sys.exit(0 if success else 1)
