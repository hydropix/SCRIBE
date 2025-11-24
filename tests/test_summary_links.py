"""
Test script to validate link injection in daily summaries
"""

import sys
import os
from pathlib import Path

# Fix encoding for Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.processors.ollama_client import OllamaClient


def test_link_injection():
    """Test the link injection functionality without calling Ollama"""

    print("\n" + "="*60)
    print("TEST: Link Injection in Summary")
    print("="*60)

    # Create a mock OllamaClient (we'll test the _inject_links_in_summary method directly)
    client = OllamaClient(
        config={'model': 'qwen3:14b', 'parameters': {}},
        prompts={'system_prompts': {}},
        language="French"
    )

    # Mock summary with bold text
    mock_summary = """**Résumé IA du Jour**

Aujourd'hui, nous avons découvert plusieurs développements importants :

* **GPT-5 améliore le raisonnement** - Une avancée majeure dans les capacités de raisonnement logique
* **Claude devient multimodal** - Support natif des images et vidéos
* **Nouvelle architecture Transformer** - Réduction de 40% de la consommation mémoire

Ces innovations montrent que l'IA continue de progresser rapidement."""

    # Mock content items with URLs
    mock_contents = [
        {
            'translated_title': 'GPT-5 améliore le raisonnement logique',
            'title': 'GPT-5 Improves Logical Reasoning',
            'url': 'https://reddit.com/r/MachineLearning/post1',
            'category': 'Models'
        },
        {
            'translated_title': 'Claude devient multimodal avec support images',
            'title': 'Claude Goes Multimodal',
            'url': 'https://reddit.com/r/artificial/post2',
            'category': 'Models'
        },
        {
            'translated_title': 'Nouvelle architecture Transformer optimisée',
            'title': 'New Transformer Architecture',
            'url': 'https://youtube.com/watch?v=abc123',
            'category': 'Research'
        }
    ]

    print("\n📝 Original Summary:")
    print("-"*60)
    print(mock_summary)
    print("-"*60)

    print("\n🔗 Available Content URLs:")
    for i, content in enumerate(mock_contents, 1):
        print(f"  {i}. {content['translated_title']}")
        print(f"     → {content['url']}")

    # Test the link injection
    print("\n⚙️  Processing link injection...")
    result = client._inject_links_in_summary(mock_summary, mock_contents)

    print("\n✨ Summary with Links:")
    print("-"*60)
    print(result)
    print("-"*60)

    # Count how many links were injected
    link_count = result.count('](')
    print(f"\n📊 Statistics:")
    print(f"  - Links injected: {link_count}")
    print(f"  - Original length: {len(mock_summary)} chars")
    print(f"  - New length: {len(result)} chars")

    # Verify that links are present
    if link_count > 0:
        print("\n✅ SUCCESS: Links were successfully injected!")
        return True
    else:
        print("\n❌ FAILURE: No links were injected")
        return False


def test_edge_cases():
    """Test edge cases for link injection"""

    print("\n" + "="*60)
    print("TEST: Edge Cases")
    print("="*60)

    client = OllamaClient(
        config={'model': 'qwen3:14b', 'parameters': {}},
        prompts={'system_prompts': {}},
        language="French"
    )

    # Test 1: No bold text
    print("\n📝 Test 1: Summary without bold text")
    summary_no_bold = "This is a summary without any bold text."
    contents = [{'translated_title': 'Test', 'url': 'https://example.com'}]
    result = client._inject_links_in_summary(summary_no_bold, contents)
    print(f"  Input: {summary_no_bold}")
    print(f"  Output: {result}")
    print(f"  ✓ No changes (expected)" if result == summary_no_bold else "  ✗ Unexpected change")

    # Test 2: Bold text with no matching content
    print("\n📝 Test 2: Bold text with no matching content")
    summary_no_match = "**Something completely different**"
    result = client._inject_links_in_summary(summary_no_match, contents)
    print(f"  Input: {summary_no_match}")
    print(f"  Output: {result}")
    print(f"  ✓ No changes (expected)" if result == summary_no_match else "  ✗ Unexpected change")

    # Test 3: Partial title match
    print("\n📝 Test 3: Partial title match")
    summary_partial = "**New AI Model** shows great results"
    contents_partial = [{'translated_title': 'New AI Model Released', 'url': 'https://example.com/ai'}]
    result = client._inject_links_in_summary(summary_partial, contents_partial)
    print(f"  Input: {summary_partial}")
    print(f"  Output: {result}")
    print(f"  ✓ Link injected" if '](https://' in result else "  ✗ No link injected")

    # Test 4: Empty content list
    print("\n📝 Test 4: Empty content list")
    summary = "**Bold text**"
    result = client._inject_links_in_summary(summary, [])
    print(f"  Input: {summary}")
    print(f"  Output: {result}")
    print(f"  ✓ No changes (expected)" if result == summary else "  ✗ Unexpected change")

    print("\n✅ Edge case tests completed")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("DAILY SUMMARY LINK INJECTION TEST SUITE")
    print("="*60)

    # Run tests
    success = test_link_injection()
    test_edge_cases()

    print("\n" + "="*60)
    if success:
        print("✅ ALL TESTS PASSED")
    else:
        print("❌ SOME TESTS FAILED")
    print("="*60 + "\n")
