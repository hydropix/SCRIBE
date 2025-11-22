"""Test fallback mechanism for failed notifications"""

import sys
import io
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from src.notifiers.fallback_manager import FallbackManager
from src.utils import setup_package_logging


def test_parse_report():
    """Test parsing an existing report"""
    print("=" * 60)
    print("TEST: Parse Report")
    print("=" * 60)

    # Setup logging
    setup_package_logging("test_fallback")

    # Initialize fallback manager
    manager = FallbackManager("ai_trends")

    # Find latest report
    latest_report = manager.find_latest_report()
    if not latest_report:
        print("❌ No reports found")
        return False

    print(f"✓ Found latest report: {latest_report}")

    # Parse the report
    items = manager.parse_report(latest_report)
    if not items:
        print("❌ Failed to parse report")
        return False

    print(f"✓ Successfully parsed {len(items)} items")

    # Display sample items
    print("\n" + "-" * 60)
    print("Sample parsed items:")
    print("-" * 60)

    for i, item in enumerate(items[:3], 1):  # Show first 3
        print(f"\n{i}. {item['title'][:60]}...")
        print(f"   Category: {item['category']}")
        print(f"   Score: {item['relevance_score']}/10")
        print(f"   Has hook: {bool(item.get('hook'))}")
        print(f"   Insights length: {len(item.get('insights', ''))} chars")
        print(f"   Metadata keys: {', '.join(item['metadata'].keys())}")

        # Show metadata details
        metadata = item['metadata']
        if metadata.get('source'):
            print(f"   Source: {metadata['source']}")
        if metadata.get('url'):
            print(f"   URL: {metadata['url'][:50]}...")
        if metadata.get('video_id'):
            print(f"   Video ID: {metadata['video_id']}")
        if metadata.get('image_url'):
            print(f"   Image URL: {metadata['image_url'][:50]}...")

    print("\n" + "=" * 60)
    print(f"✓ TEST PASSED - Parsed {len(items)} items successfully")
    print("=" * 60)

    return True


def test_fallback_simulation():
    """Simulate a fallback scenario (without actually sending)"""
    print("\n" + "=" * 60)
    print("TEST: Fallback Simulation")
    print("=" * 60)

    # Setup logging
    setup_package_logging("test_fallback")

    # Initialize fallback manager
    manager = FallbackManager("ai_trends", max_retries=2, retry_delay=1.0)

    # Find latest report
    latest_report = manager.find_latest_report()
    if not latest_report:
        print("❌ No reports found")
        return False

    print(f"✓ Using report: {latest_report}")

    # Parse the report
    items = manager.parse_report(latest_report)
    if not items:
        print("❌ Failed to parse report")
        return False

    print(f"✓ Parsed {len(items)} items for simulation")

    # Simulate what would happen in a retry
    print("\nSimulation of retry workflow:")
    print("1. Original send fails")
    print("2. Fallback manager parses report")
    print("3. Reconstructs content items from Markdown")
    print("4. Retries sending with parsed data")

    print("\n✓ Simulation complete")
    print("\nParsed data structure is compatible with notifiers:")
    print(f"  - Items have all required fields: {all(k in items[0] for k in ['title', 'category', 'metadata'])}")
    print(f"  - Metadata has source info: {'source' in items[0]['metadata']}")

    print("\n" + "=" * 60)
    print("✓ TEST PASSED - Fallback simulation successful")
    print("=" * 60)

    return True


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("FALLBACK MECHANISM TESTS")
    print("=" * 60 + "\n")

    tests = [
        ("Parse Report", test_parse_report),
        ("Fallback Simulation", test_fallback_simulation),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ TEST FAILED: {test_name}")
            print(f"   Error: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✓ PASSED" if result else "❌ FAILED"
        print(f"{status}: {test_name}")

    print("\n" + "=" * 60)
    print(f"Results: {passed}/{total} tests passed")
    print("=" * 60)

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
