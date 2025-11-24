"""Live test of fallback mechanism with actual Discord/Synology sending"""

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
from src.notifiers.discord_notifier import DiscordNotifier
from src.notifiers.synology_notifier import SynologyNotifier
from src.utils import setup_package_logging, load_env_variables
from src.package_manager import PackageManager


def test_discord_fallback():
    """Test fallback mechanism with Discord notifier"""
    print("=" * 60)
    print("LIVE TEST: Discord Fallback")
    print("=" * 60)

    # Setup
    setup_package_logging("test_fallback_live")
    load_env_variables()

    # Load package config
    pm = PackageManager()
    pkg = pm.load_package("ai_trends")

    # Initialize fallback manager
    fallback_config = pkg.settings.get('fallback', {})
    fallback_manager = FallbackManager(
        package_name="ai_trends",
        max_retries=fallback_config.get('max_retries', 3),
        retry_delay=fallback_config.get('retry_delay', 5.0)
    )

    # Find latest report
    latest_report = fallback_manager.find_latest_report()
    if not latest_report:
        print("❌ No reports found")
        return False

    print(f"✓ Using report: {latest_report}")

    # Initialize Discord notifier
    discord_config = pkg.settings.get('discord', {})
    discord_notifier = DiscordNotifier(config=discord_config)

    if not discord_notifier.webhook_url:
        print("⚠️  Discord webhook not configured, skipping Discord test")
        return None

    # Check if rich embeds enabled
    use_rich_embeds = discord_config.get('rich_embeds', True)
    send_method = 'send_rich_report' if use_rich_embeds else 'send_full_report'

    print(f"\n📤 Sending via fallback mechanism...")
    print(f"   Method: {send_method}")
    print(f"   Rich embeds: {use_rich_embeds}")

    # Trigger fallback (simulates a failed original send)
    success = fallback_manager.retry_with_fallback(
        notifier=discord_notifier,
        send_method=send_method,
        report_path=latest_report,
        mention_role=discord_config.get('mention_role', '')
    )

    if success:
        print("\n✓ Discord fallback succeeded!")
        return True
    else:
        print("\n❌ Discord fallback failed")
        return False


def test_synology_fallback():
    """Test fallback mechanism with Synology notifier"""
    print("\n" + "=" * 60)
    print("LIVE TEST: Synology Fallback")
    print("=" * 60)

    # Setup
    setup_package_logging("test_fallback_live")
    load_env_variables()

    # Load package config
    pm = PackageManager()
    pkg = pm.load_package("ai_trends")

    # Initialize fallback manager
    fallback_config = pkg.settings.get('fallback', {})
    fallback_manager = FallbackManager(
        package_name="ai_trends",
        max_retries=fallback_config.get('max_retries', 3),
        retry_delay=fallback_config.get('retry_delay', 5.0)
    )

    # Find latest report
    latest_report = fallback_manager.find_latest_report()
    if not latest_report:
        print("❌ No reports found")
        return False

    print(f"✓ Using report: {latest_report}")

    # Initialize Synology notifier
    synology_config = pkg.settings.get('synology', {})
    synology_notifier = SynologyNotifier(
        config=synology_config,
        package_display_name=pkg.display_name
    )

    if not synology_notifier.webhook_url:
        print("⚠️  Synology webhook not configured, skipping Synology test")
        return None

    print(f"\n📤 Sending via fallback mechanism...")
    print(f"   Method: send_rich_report")

    # Trigger fallback (simulates a failed original send)
    success = fallback_manager.retry_with_fallback(
        notifier=synology_notifier,
        send_method='send_rich_report',
        report_path=latest_report,
        mention=synology_config.get('mention', '')
    )

    if success:
        print("\n✓ Synology fallback succeeded!")
        return True
    else:
        print("\n❌ Synology fallback failed")
        return False


def main():
    """Run live fallback tests"""
    print("\n" + "=" * 60)
    print("LIVE FALLBACK TESTS")
    print("=" * 60)
    print("\nThis will actually send notifications using the fallback mechanism")
    print("Make sure your webhooks are configured in .env")
    print("=" * 60 + "\n")

    tests = [
        ("Discord Fallback", test_discord_fallback),
        ("Synology Fallback", test_synology_fallback),
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

    for test_name, result in results:
        if result is None:
            status = "⚠️  SKIPPED"
        elif result:
            status = "✓ PASSED"
        else:
            status = "❌ FAILED"
        print(f"{status}: {test_name}")

    passed = sum(1 for _, result in results if result is True)
    skipped = sum(1 for _, result in results if result is None)
    total = len(results)

    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {skipped} skipped, {total - passed - skipped} failed")
    print("=" * 60)

    return passed > 0 or skipped == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
