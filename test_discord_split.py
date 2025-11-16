#!/usr/bin/env python3
"""Test script to verify Discord message splitting with the latest report"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.notifiers.discord_notifier import DiscordNotifier


def extract_executive_summary(report_path: str) -> str:
    """Extract the executive summary from a report file"""
    with open(report_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find executive summary section
    start_marker = "## 📊 Résumé Exécutif"

    start_idx = content.find(start_marker)
    if start_idx == -1:
        return "No executive summary found"

    # Move past the marker and any newlines
    content_start = start_idx + len(start_marker)

    # Find the next section (starts with ---)
    next_section = content.find("\n---", content_start)
    if next_section == -1:
        return "No executive summary found"

    # Extract the summary text
    summary_section = content[content_start:next_section].strip()

    # If wrapped in ```markdown block, extract just the content
    if summary_section.startswith("```markdown"):
        summary_section = summary_section[len("```markdown"):].strip()
        if summary_section.endswith("```"):
            summary_section = summary_section[:-3].strip()

    return summary_section


def extract_metrics(report_path: str) -> dict:
    """Extract metrics from a report file"""
    with open(report_path, 'r', encoding='utf-8') as f:
        content = f.read()

    metrics = {
        'total_analyzed': 0,
        'relevant_count': 0,
        'relevant_percentage': 0.0,
        'average_score': 0.0,
        'by_source': {},
        'categories_distribution': {}
    }

    # Parse basic metrics
    import re

    total_match = re.search(r'\*\*Total de contenus analysés\*\*:\s*(\d+)', content)
    if total_match:
        metrics['total_analyzed'] = int(total_match.group(1))

    relevant_match = re.search(r'\*\*Contenus pertinents\*\*:\s*(\d+)\s*\((\d+\.?\d*)%\)', content)
    if relevant_match:
        metrics['relevant_count'] = int(relevant_match.group(1))
        metrics['relevant_percentage'] = float(relevant_match.group(2))

    score_match = re.search(r'\*\*Score de pertinence moyen\*\*:\s*(\d+\.?\d*)/10', content)
    if score_match:
        metrics['average_score'] = float(score_match.group(1))

    # Parse sources
    sources_section = re.search(r'\*\*Sources\*\*:\s*\n(.*?)(?=\n\n|\n---)', content, re.DOTALL)
    if sources_section:
        source_matches = re.findall(r'-\s*(\w+):\s*(\d+)', sources_section.group(1))
        for source, count in source_matches:
            metrics['by_source'][source.lower()] = int(count)

    # Parse categories
    categories_section = re.search(r'\*\*Distribution par catégorie\*\*:\s*\n(.*?)(?=\*\*Sources\*\*)', content, re.DOTALL)
    if categories_section:
        cat_matches = re.findall(r'-\s*(.+?):\s*(\d+)', categories_section.group(1))
        for cat, count in cat_matches:
            metrics['categories_distribution'][cat.strip()] = int(count)

    return metrics


def main():
    print("=" * 60)
    print("Testing Discord Full Report Sending")
    print("=" * 60)

    # Initialize notifier
    notifier = DiscordNotifier()

    if not notifier.webhook_url:
        print("ERROR: DISCORD_WEBHOOK_URL not configured in .env")
        print("Please set DISCORD_WEBHOOK_URL in your .env file")
        return

    # Load the latest report
    report_path = "data/reports/veille_ia_2025-11-16.md"

    if not os.path.exists(report_path):
        print(f"ERROR: Report not found at {report_path}")
        return

    print(f"Loading report: {report_path}")

    # Read the full report
    with open(report_path, 'r', encoding='utf-8') as f:
        report_content = f.read()

    # Clean the content
    cleaned_content = notifier._clean_markdown_for_discord(report_content)

    print(f"\nFull report length: {len(report_content)} characters")
    print(f"Cleaned report length: {len(cleaned_content)} characters")

    # Test the splitting
    chunks = notifier._split_message(cleaned_content)
    print(f"\nReport will be split into {len(chunks)} part(s)")

    for i, chunk in enumerate(chunks, 1):
        print(f"Part {i}: {len(chunk)} characters")

    # Estimate time
    total_time = len(chunks) * notifier.MESSAGE_DELAY
    print(f"\nEstimated sending time: {total_time:.1f} seconds")

    # Send automatically
    print("\n" + "=" * 60)
    print("Sending full report to Discord...")
    print("This may take a while due to rate limiting delays...")
    print("=" * 60)

    success = notifier.send_full_report(report_path=report_path, mention_role="")

    if success:
        print("\nSUCCESS! Full report sent to Discord.")
    else:
        print("\nFAILED to send full report to Discord.")


if __name__ == "__main__":
    main()
