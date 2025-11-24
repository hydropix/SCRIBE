#!/usr/bin/env python3
"""CLI tool to manually resend reports using fallback mechanism"""

import sys
import io
import argparse
from pathlib import Path
from datetime import datetime

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.package_manager import PackageManager
from src.notifiers.fallback_manager import FallbackManager
from src.notifiers.discord_notifier import DiscordNotifier
from src.notifiers.synology_notifier import SynologyNotifier
from src.processors.ollama_client import OllamaClient
from src.utils import setup_package_logging, load_env_variables


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Manually resend SCRIBE reports using fallback mechanism',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Resend latest report (both Discord and Synology)
  python -m src.cli.resend_report --package ai_trends

  # Resend specific date
  python -m src.cli.resend_report --package ai_trends --date 2025-11-22

  # Discord only
  python -m src.cli.resend_report --package ai_trends --discord-only

  # Synology only
  python -m src.cli.resend_report --package ai_trends --synology-only

  # Preview without sending
  python -m src.cli.resend_report --package ai_trends --dry-run

  # Use text mode instead of rich embeds for Discord
  python -m src.cli.resend_report --package ai_trends --text-only

  # Send daily summary instead of full report
  python -m src.cli.resend_report --package ai_trends --summary --discord-only
        """
    )

    parser.add_argument(
        '--package',
        required=True,
        help='Package name (e.g., ai_trends)'
    )

    parser.add_argument(
        '--date',
        help='Report date (YYYY-MM-DD). If not specified, uses latest report'
    )

    parser.add_argument(
        '--discord-only',
        action='store_true',
        help='Send to Discord only (skip Synology)'
    )

    parser.add_argument(
        '--synology-only',
        action='store_true',
        help='Send to Synology only (skip Discord)'
    )

    parser.add_argument(
        '--text-only',
        action='store_true',
        help='Use text mode instead of rich embeds for Discord'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview without actually sending'
    )

    parser.add_argument(
        '--no-retry',
        action='store_true',
        help='Disable retry mechanism (single attempt only)'
    )

    parser.add_argument(
        '--summary',
        action='store_true',
        help='Send daily summary instead of full report'
    )

    return parser.parse_args()


def preview_report(fallback_manager: FallbackManager, report_path: str):
    """Show report preview"""
    print("\n" + "=" * 60)
    print("📄 REPORT PREVIEW")
    print("=" * 60)

    items = fallback_manager.parse_report(report_path)
    if not items:
        print("❌ Failed to parse report")
        return False

    print(f"\n✓ Report: {Path(report_path).name}")
    print(f"✓ Total items: {len(items)}")

    # Group by category
    by_category = {}
    for item in items:
        category = item.get('category', 'Other')
        if category not in by_category:
            by_category[category] = []
        by_category[category].append(item)

    print(f"✓ Categories: {len(by_category)}")
    print("\n" + "-" * 60)
    print("Items by category:")
    print("-" * 60)

    for category, cat_items in by_category.items():
        print(f"\n📁 {category} ({len(cat_items)} item{'s' if len(cat_items) > 1 else ''})")
        for i, item in enumerate(cat_items[:3], 1):  # Show first 3
            print(f"  {i}. {item['title'][:70]}...")
            print(f"     Score: {item['relevance_score']}/10")
        if len(cat_items) > 3:
            print(f"  ... and {len(cat_items) - 3} more")

    print("\n" + "=" * 60)
    return True


def send_summary_to_discord(
    fallback_manager: FallbackManager,
    discord_notifier: DiscordNotifier,
    ollama_client: OllamaClient,
    report_path: str,
    mention_role: str
):
    """Send daily summary to Discord"""
    print("\n" + "=" * 60)
    print("📤 SENDING SUMMARY TO DISCORD")
    print("=" * 60)

    if not discord_notifier.summary_webhook_url:
        print("❌ Discord summary webhook not configured")
        return False

    print(f"Webhook: {discord_notifier.summary_webhook_url[:50]}...")

    try:
        # Parse report to extract items
        print("\n⏳ Parsing report and generating summary...")
        items = fallback_manager.parse_report(report_path)
        if not items:
            print("❌ Failed to parse report")
            return False

        print(f"✓ Parsed {len(items)} items")

        # Generate daily summary using Ollama
        print("⏳ Generating daily summary with Ollama...")
        summary_text = ollama_client.generate_daily_summary(items)

        if not summary_text:
            print("❌ Failed to generate summary")
            return False

        print(f"✓ Generated summary ({len(summary_text)} chars)")

        # Send the summary
        print("\n⏳ Sending to Discord...")
        success = discord_notifier.send_summary(
            summary_text=summary_text,
            mention_role=mention_role
        )

        if success:
            print("\n✓ Discord summary send succeeded!")
            return True
        else:
            print("\n❌ Discord summary send failed")
            return False

    except Exception as e:
        print(f"❌ Error generating/sending summary: {e}")
        return False


def send_to_discord(
    fallback_manager: FallbackManager,
    discord_notifier: DiscordNotifier,
    report_path: str,
    use_rich: bool,
    mention_role: str,
    no_retry: bool
):
    """Send report to Discord"""
    print("\n" + "=" * 60)
    print("📤 SENDING TO DISCORD")
    print("=" * 60)

    if not discord_notifier.webhook_url:
        print("❌ Discord webhook not configured")
        return False

    send_method = 'send_rich_report' if use_rich else 'send_full_report'
    print(f"Method: {send_method}")
    print(f"Webhook: {discord_notifier.webhook_url[:50]}...")

    if no_retry:
        # Direct send without retry
        print("\nSending (no retry)...")
        items = fallback_manager.parse_report(report_path)
        if not items:
            print("❌ Failed to parse report")
            return False

        if use_rich:
            success = discord_notifier.send_rich_report(
                relevant_contents=items,
                mention_role=mention_role
            )
        else:
            success = discord_notifier.send_full_report(
                report_path=report_path,
                mention_role=mention_role
            )
    else:
        # Use fallback mechanism with retry
        print("\nSending via fallback mechanism (with retry)...")
        success = fallback_manager.retry_with_fallback(
            notifier=discord_notifier,
            send_method=send_method,
            report_path=report_path,
            mention_role=mention_role
        )

    if success:
        print("\n✓ Discord send succeeded!")
        return True
    else:
        print("\n❌ Discord send failed")
        return False


def send_summary_to_synology(
    fallback_manager: FallbackManager,
    synology_notifier: SynologyNotifier,
    ollama_client: OllamaClient,
    report_path: str,
    mention: str
):
    """Send daily summary to Synology"""
    print("\n" + "=" * 60)
    print("📤 SENDING SUMMARY TO SYNOLOGY CHAT")
    print("=" * 60)

    if not synology_notifier.summary_webhook_url:
        print("❌ Synology summary webhook not configured")
        return False

    print(f"Webhook: {synology_notifier.summary_webhook_url[:50]}...")

    try:
        # Parse report to extract items
        print("\n⏳ Parsing report and generating summary...")
        items = fallback_manager.parse_report(report_path)
        if not items:
            print("❌ Failed to parse report")
            return False

        print(f"✓ Parsed {len(items)} items")

        # Generate daily summary using Ollama
        print("⏳ Generating daily summary with Ollama...")
        summary_text = ollama_client.generate_daily_summary(items)

        if not summary_text:
            print("❌ Failed to generate summary")
            return False

        print(f"✓ Generated summary ({len(summary_text)} chars)")

        # Send the summary
        print("\n⏳ Sending to Synology Chat...")
        success = synology_notifier.send_summary(
            summary_text=summary_text,
            mention=mention
        )

        if success:
            print("\n✓ Synology summary send succeeded!")
            return True
        else:
            print("\n❌ Synology summary send failed")
            return False

    except Exception as e:
        print(f"❌ Error generating/sending summary: {e}")
        return False


def send_to_synology(
    fallback_manager: FallbackManager,
    synology_notifier: SynologyNotifier,
    report_path: str,
    mention: str,
    no_retry: bool
):
    """Send report to Synology"""
    print("\n" + "=" * 60)
    print("📤 SENDING TO SYNOLOGY CHAT")
    print("=" * 60)

    if not synology_notifier.webhook_url:
        print("❌ Synology webhook not configured")
        return False

    print(f"Webhook: {synology_notifier.webhook_url[:50]}...")

    if no_retry:
        # Direct send without retry
        print("\nSending (no retry)...")
        items = fallback_manager.parse_report(report_path)
        if not items:
            print("❌ Failed to parse report")
            return False

        success = synology_notifier.send_rich_report(
            relevant_contents=items,
            mention=mention
        )
    else:
        # Use fallback mechanism with retry
        print("\nSending via fallback mechanism (with retry)...")
        success = fallback_manager.retry_with_fallback(
            notifier=synology_notifier,
            send_method='send_rich_report',
            report_path=report_path,
            mention=mention
        )

    if success:
        print("\n✓ Synology send succeeded!")
        return True
    else:
        print("\n❌ Synology send failed")
        return False


def main():
    """Main CLI entry point"""
    args = parse_args()

    # Print header
    print("\n" + "=" * 60)
    if args.summary:
        print("🔄 SCRIBE SUMMARY RESENDER")
    else:
        print("🔄 SCRIBE REPORT RESENDER")
    print("=" * 60)
    print(f"Package: {args.package}")
    if args.date:
        print(f"Date: {args.date}")
    else:
        print("Date: Latest")
    if args.summary:
        print("Type: SUMMARY")
    if args.dry_run:
        print("Mode: DRY RUN (preview only)")
    print("=" * 60)

    # Setup
    setup_package_logging(args.package)
    load_env_variables()

    # Load package
    try:
        pm = PackageManager()
        pkg = pm.load_package(args.package)
    except Exception as e:
        print(f"\n❌ Failed to load package '{args.package}': {e}")
        return 1

    # Initialize fallback manager
    fallback_config = pkg.settings.get('fallback', {})
    fallback_manager = FallbackManager(
        package_name=args.package,
        max_retries=fallback_config.get('max_retries', 3),
        retry_delay=fallback_config.get('retry_delay', 5.0)
    )

    # Find report
    report_path = fallback_manager.find_latest_report(args.date)
    if not report_path:
        print(f"\n❌ No report found for package '{args.package}'")
        if args.date:
            print(f"   Date: {args.date}")
        return 1

    print(f"\n✓ Found report: {report_path}")

    # Preview
    if not preview_report(fallback_manager, report_path):
        return 1

    # Dry run - exit here
    if args.dry_run:
        print("\n" + "=" * 60)
        print("DRY RUN - No notifications sent")
        print("=" * 60)
        return 0

    # Initialize Ollama client (needed for summary generation)
    ollama_client = None
    if args.summary:
        ollama_config = pkg.get_ollama_config()
        ollama_client = OllamaClient(
            config=ollama_config,
            prompts=pkg.prompts,
            language=pkg.settings.get('reports', {}).get('language', 'en')
        )

    # Initialize notifiers
    discord_config = pkg.settings.get('discord', {})
    discord_notifier = DiscordNotifier(
        config=discord_config,
        package_display_name=pkg.display_name
    )

    synology_config = pkg.settings.get('synology', {})
    synology_notifier = SynologyNotifier(
        config=synology_config,
        package_display_name=pkg.display_name
    )

    # Send to Discord
    discord_success = None
    if not args.synology_only:
        if args.summary:
            # Send summary
            discord_success = send_summary_to_discord(
                fallback_manager=fallback_manager,
                discord_notifier=discord_notifier,
                ollama_client=ollama_client,
                report_path=report_path,
                mention_role=discord_config.get('summary', {}).get('mention_role', '')
            )
        else:
            # Send full report
            use_rich = not args.text_only and discord_config.get('rich_embeds', True)
            discord_success = send_to_discord(
                fallback_manager=fallback_manager,
                discord_notifier=discord_notifier,
                report_path=report_path,
                use_rich=use_rich,
                mention_role=discord_config.get('mention_role', ''),
                no_retry=args.no_retry
            )

    # Send to Synology
    synology_success = None
    if not args.discord_only:
        if args.summary:
            # Send summary
            synology_success = send_summary_to_synology(
                fallback_manager=fallback_manager,
                synology_notifier=synology_notifier,
                ollama_client=ollama_client,
                report_path=report_path,
                mention=synology_config.get('summary', {}).get('mention', '')
            )
        else:
            # Send full report
            synology_success = send_to_synology(
                fallback_manager=fallback_manager,
                synology_notifier=synology_notifier,
                report_path=report_path,
                mention=synology_config.get('mention', ''),
                no_retry=args.no_retry
            )

    # Summary
    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)

    if discord_success is not None:
        status = "✓ SUCCESS" if discord_success else "❌ FAILED"
        print(f"Discord: {status}")

    if synology_success is not None:
        status = "✓ SUCCESS" if synology_success else "❌ FAILED"
        print(f"Synology: {status}")

    print("=" * 60)

    # Exit code
    if discord_success is False or synology_success is False:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
