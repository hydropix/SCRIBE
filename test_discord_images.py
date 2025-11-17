#!/usr/bin/env python3
"""
Test script for Discord rich embeds with images
Tests the new image extraction and Discord embed functionality
"""

import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.utils import load_env_variables, setup_logging
from src.notifiers.discord_notifier import DiscordNotifier


def test_embed_creation():
    """Test that embeds are created correctly with image URLs"""

    print("=" * 60)
    print("Testing Discord Embed Creation with Images")
    print("=" * 60)

    notifier = DiscordNotifier()

    # Test content with Reddit image
    test_contents = [
        {
            'title': 'GPT-5 Architecture Diagram Released',
            'translated_title': 'Diagramme de l\'architecture GPT-5 publié',
            'hook': 'OpenAI dévoile enfin les détails techniques de son nouveau modèle.',
            'is_relevant': True,
            'relevance_score': 9,
            'category': 'Large Language Models',
            'insights': '**Points clés:**\n- Architecture hybride attention/MoE\n- 10x plus efficace que GPT-4\n- Support multimodal natif',
            'metadata': {
                'source': 'reddit',
                'permalink': 'https://reddit.com/r/MachineLearning/comments/example',
                'author': 'ml_researcher',
                'subreddit': 'MachineLearning',
                'created_utc': datetime.now(),
                'image_url': 'https://i.redd.it/example_architecture_diagram.png'  # Reddit image
            }
        },
        {
            'title': 'New Vision Transformer Explained',
            'translated_title': 'Nouveau Vision Transformer expliqué en détail',
            'hook': 'Une avancée majeure dans la compréhension visuelle par IA.',
            'is_relevant': True,
            'relevance_score': 8,
            'category': 'Computer Vision',
            'insights': '**Résumé:**\n- Dépasse les performances de CLIP\n- Entraînement auto-supervisé\n- Applications en robotique',
            'metadata': {
                'source': 'youtube',
                'url': 'https://youtube.com/watch?v=dQw4w9WgXcQ',
                'channel_title': 'AI Explained',
                'published_at': '2024-01-15T10:00:00Z',
                'video_id': 'dQw4w9WgXcQ'  # YouTube video ID for thumbnail
            }
        },
        {
            'title': 'AI Ethics Framework Proposed',
            'translated_title': 'Nouveau cadre éthique pour l\'IA proposé',
            'hook': 'Des chercheurs établissent de nouvelles normes.',
            'is_relevant': True,
            'relevance_score': 7,
            'category': 'AI Ethics & Safety',
            'insights': 'Un nouveau framework pour évaluer les risques IA.',
            'metadata': {
                'source': 'reddit',
                'permalink': 'https://reddit.com/r/AIethics/comments/example2',
                'author': 'ethics_expert',
                'subreddit': 'AIethics',
                'created_utc': datetime.now(),
                'image_url': None  # No image for this post
            }
        }
    ]

    # Test embed creation
    print("\n1. Testing embed creation for each content type...")

    for i, content in enumerate(test_contents, 1):
        embed = notifier._create_content_embed(content)

        print(f"\n--- Embed {i} ---")
        print(f"Title: {embed['title'][:50]}...")
        print(f"Color: {hex(embed['color'])}")
        print(f"URL: {embed.get('url', 'N/A')}")

        if 'image' in embed:
            print(f"Image URL: {embed['image']['url'][:60]}...")
        else:
            print("Image: None")

        if 'thumbnail' in embed:
            print(f"Thumbnail: {embed['thumbnail']['url'][:60]}...")
        else:
            print("Thumbnail: None")

        print(f"Footer: {embed['footer']['text']}")
        print(f"Author: {embed.get('author', {}).get('name', 'N/A')}")

    # Test header message
    print("\n\n2. Testing header message creation...")
    header = notifier._create_header_message(len(test_contents), "@everyone")
    print(header[:200] + "...")

    # Test category colors
    print("\n\n3. Testing category colors...")
    categories = [
        "Large Language Models",
        "Computer Vision",
        "Robotics",
        "AI Ethics",
        "Unknown Category"
    ]
    for cat in categories:
        color = notifier._get_category_color(cat)
        print(f"  {cat}: {hex(color)}")

    print("\n" + "=" * 60)
    print("Embed creation tests completed successfully!")
    print("=" * 60)

    return test_contents


def test_send_to_discord(test_contents):
    """
    Optional: Send test embeds to Discord
    Only runs if DISCORD_WEBHOOK_URL is configured
    """
    print("\n" + "=" * 60)
    print("Testing Discord Send (requires webhook)")
    print("=" * 60)

    try:
        load_env_variables()
    except FileNotFoundError:
        print("No .env file found. Skipping Discord send test.")
        return

    notifier = DiscordNotifier()

    if not notifier.webhook_url:
        print("DISCORD_WEBHOOK_URL not configured. Skipping send test.")
        return

    print("\nWebhook URL configured. Ready to send test embeds.")

    response = input("\nDo you want to send test embeds to Discord? (yes/no): ")

    if response.lower() in ['yes', 'y', 'oui', 'o']:
        print("\nSending rich report to Discord...")
        success = notifier.send_rich_report(
            relevant_contents=test_contents,
            mention_role=""  # No mention for test
        )

        if success:
            print("Test embeds sent successfully! Check your Discord channel.")
        else:
            print("Failed to send test embeds. Check logs for details.")
    else:
        print("Skipping Discord send test.")


def test_image_url_extraction_logic():
    """Test the image URL extraction patterns"""

    print("\n" + "=" * 60)
    print("Testing Image URL Detection Patterns")
    print("=" * 60)

    # Mock post object for testing
    class MockPost:
        def __init__(self, url, preview=None, is_gallery=False, media_metadata=None):
            self.id = "test123"
            self.url = url
            self.preview = preview
            self.is_gallery = is_gallery
            self.media_metadata = media_metadata or {}
            self.thumbnail = "default"

    test_cases = [
        ("Direct JPG", "https://i.redd.it/example.jpg"),
        ("Direct PNG", "https://example.com/image.png"),
        ("Direct GIF", "https://imgur.com/animation.gif"),
        ("Imgur page", "https://imgur.com/abc123"),
        ("Imgur album (not supported)", "https://imgur.com/a/album123"),
        ("External link (no image)", "https://arxiv.org/paper/123"),
        ("i.redd.it URL", "https://i.redd.it/randomid123"),
    ]

    for name, url in test_cases:
        post = MockPost(url)

        # Check URL patterns
        has_image = False
        reason = ""

        if any(url.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
            has_image = True
            reason = "Direct image extension"
        elif 'i.redd.it' in url:
            has_image = True
            reason = "Reddit hosted"
        elif 'imgur.com' in url and '/a/' not in url and '/gallery/' not in url:
            has_image = True
            reason = "Imgur direct"

        print(f"\n{name}:")
        print(f"  URL: {url}")
        print(f"  Has image: {has_image}")
        if has_image:
            print(f"  Reason: {reason}")

    # Test preview extraction
    print("\n\nTesting preview extraction:")
    preview = {
        'images': [{
            'source': {
                'url': 'https://preview.redd.it/example.png?auto=webp&amp;s=abc123'
            }
        }]
    }
    post_with_preview = MockPost("https://example.com", preview=preview)
    print(f"  Preview URL (encoded): {preview['images'][0]['source']['url']}")
    print(f"  Decoded: {preview['images'][0]['source']['url'].replace('&amp;', '&')}")


if __name__ == "__main__":
    setup_logging()

    # Run tests
    test_image_url_extraction_logic()
    test_contents = test_embed_creation()
    test_send_to_discord(test_contents)

    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)
