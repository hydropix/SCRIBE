"""Test script to verify package display names in reports and notifications"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.package_manager import PackageManager
from src.notifiers.discord_notifier import DiscordNotifier
from src.notifiers.synology_notifier import SynologyNotifier
from src.storage.report_generator import ReportGenerator


def test_package_display_names():
    """Test that package display names are correctly used in all components"""

    print("\n" + "=" * 60)
    print("Testing Package Display Names")
    print("=" * 60)

    # Load all packages
    pm = PackageManager()
    package_names = pm.list_packages()

    if not package_names:
        print("❌ No packages found")
        return False

    print(f"\nFound {len(package_names)} package(s):")

    # Test each package
    all_passed = True
    for pkg_name in package_names:
        pkg = pm.load_package(pkg_name)
        print(f"  - {pkg_name}: '{pkg.display_name}'")
        print(f"\n{'-' * 60}")
        print(f"Testing package: {pkg_name}")
        print(f"Display name: {pkg.display_name}")
        print(f"{'-' * 60}")

        # Test Discord Notifier
        print("\n1. Discord Notifier")
        discord_config = pkg.settings.get('discord', {})
        discord_notifier = DiscordNotifier(
            config=discord_config,
            package_display_name=pkg.display_name
        )

        # Create a test header
        test_header = discord_notifier._create_header_message(total_insights=5)
        if pkg.display_name.upper() in test_header:
            print(f"   [OK] Discord header contains correct display name")
            print(f"   Preview: {test_header[:80]}...")
        else:
            print(f"   [FAIL] Discord header missing display name")
            print(f"   Got: {test_header[:100]}")
            all_passed = False

        # Test Synology Notifier
        print("\n2. Synology Notifier")
        synology_config = pkg.settings.get('synology', {})
        synology_notifier = SynologyNotifier(
            config=synology_config,
            package_display_name=pkg.display_name
        )

        test_header = synology_notifier._create_header_message(total_insights=5)
        if pkg.display_name.upper() in test_header:
            print(f"   [OK] Synology header contains correct display name")
            print(f"   Preview: {test_header[:80]}...")
        else:
            print(f"   [FAIL] Synology header missing display name")
            print(f"   Got: {test_header[:100]}")
            all_passed = False

        # Test Report Generator
        print("\n3. Report Generator")
        report_generator = ReportGenerator(
            package_name=pkg.name,
            config=pkg.settings,
            prompts=pkg.prompts,
            ollama_config=pkg.get_ollama_config(),
            package_display_name=pkg.display_name
        )

        # Create a test report with minimal data
        from datetime import datetime
        test_report = report_generator._build_markdown(
            by_category={"Test Category": []},
            statistics=None,
            report_date=datetime.now()
        )

        if pkg.display_name.upper() in test_report:
            print(f"   [OK] Report header contains correct display name")
            # Skip preview to avoid emoji encoding issues on Windows
        else:
            print(f"   [FAIL] Report header missing display name")
            all_passed = False

    print(f"\n{'=' * 60}")
    if all_passed:
        print("[SUCCESS] ALL TESTS PASSED")
    else:
        print("[ERROR] SOME TESTS FAILED")
    print("=" * 60)

    return all_passed


if __name__ == "__main__":
    success = test_package_display_names()
    exit(0 if success else 1)
