"""Fallback manager for retrying failed notifications using persisted reports"""

import logging
import re
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime


class FallbackManager:
    """Manages fallback retry mechanism for failed notifications"""

    def __init__(self, package_name: str, max_retries: int = 3, retry_delay: float = 5.0):
        """
        Initialize fallback manager

        Args:
            package_name: Name of the package
            max_retries: Maximum number of retry attempts
            retry_delay: Delay in seconds between retries
        """
        self.logger = logging.getLogger("SCRIBE.FallbackManager")
        self.package_name = package_name
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # Report directory
        self.report_dir = Path("data") / package_name / "reports"

        self.logger.info(f"Fallback manager initialized (package: {package_name}, max_retries: {max_retries})")

    def parse_report(self, report_path: str) -> Optional[List[Dict[str, Any]]]:
        """
        Parse a Markdown report to extract content items

        Args:
            report_path: Path to the report file

        Returns:
            List of content dictionaries compatible with notifiers, or None if parsing fails
        """
        try:
            with open(report_path, 'r', encoding='utf-8') as f:
                content = f.read()

            self.logger.info(f"Parsing report: {report_path}")

            # Extract all content items
            items = []

            # Split by category sections (## heading)
            category_pattern = r'## (.+?)\n\n\*(\d+) insight\(s\)\*\n\n(.+?)(?=\n## |\n---\n\n---\n|$)'
            category_matches = re.finditer(category_pattern, content, re.DOTALL)

            for category_match in category_matches:
                category = category_match.group(1).strip()
                category_content = category_match.group(3)

                # Extract individual items within this category (### heading)
                item_pattern = r'### \d+\. (.+?)\n\n(?:<!-- (.+?) -->\n\n)?(?:\*(.+?)\*\n\n)?(.+?)(?=\n### |\n\n---\n|$)'
                item_matches = re.finditer(item_pattern, category_content, re.DOTALL)

                for item_match in item_matches:
                    title = item_match.group(1).strip()
                    hidden_meta_str = item_match.group(2)  # HTML comment metadata
                    hook = item_match.group(3).strip() if item_match.group(3) else None
                    body = item_match.group(4).strip()

                    # Extract insights (everything before metadata section)
                    metadata_marker = body.find('📎 **Metadata**')
                    if metadata_marker != -1:
                        insights = body[:metadata_marker].strip()
                        metadata_text = body[metadata_marker:]
                    else:
                        insights = body
                        metadata_text = ""

                    # Parse metadata (visible)
                    metadata = self._parse_metadata(metadata_text)

                    # Parse hidden metadata from HTML comment
                    if hidden_meta_str:
                        hidden_meta = self._parse_hidden_metadata(hidden_meta_str)
                        metadata.update(hidden_meta)

                    # Extract relevance score from metadata text
                    score_match = re.search(r'Relevance: (\d+)/10', metadata_text)
                    relevance_score = int(score_match.group(1)) if score_match else 7

                    # Build content item
                    item = {
                        'title': title,
                        'translated_title': title,  # Already translated in report
                        'hook': hook,
                        'insights': insights,
                        'category': category,
                        'relevance_score': relevance_score,
                        'is_relevant': True,
                        'metadata': metadata
                    }

                    items.append(item)
                    self.logger.debug(f"Parsed item: {title[:50]}... (category: {category})")

            self.logger.info(f"Successfully parsed {len(items)} items from report")
            return items if items else None

        except FileNotFoundError:
            self.logger.error(f"Report file not found: {report_path}")
            return None
        except Exception as e:
            self.logger.error(f"Failed to parse report: {e}", exc_info=True)
            return None

    def _parse_metadata(self, metadata_text: str) -> Dict[str, Any]:
        """
        Parse metadata section from report

        Args:
            metadata_text: The metadata section text

        Returns:
            Dictionary of metadata fields
        """
        metadata = {}

        # Extract URL (Source link)
        url_match = re.search(r'\[Source\]\((.+?)\)', metadata_text)
        if url_match:
            url = url_match.group(1)
            metadata['url'] = url
            metadata['permalink'] = url

        # Extract author
        author_match = re.search(r'Author: (.+?)(?:\n|$)', metadata_text)
        if author_match:
            metadata['author'] = author_match.group(1).strip()

        # Extract channel
        channel_match = re.search(r'Channel: (.+?)(?:\n|$)', metadata_text)
        if channel_match:
            metadata['channel_title'] = channel_match.group(1).strip()

        # Extract date
        date_match = re.search(r'Date: (.+?)(?:\n|$)', metadata_text)
        if date_match:
            metadata['created_utc'] = date_match.group(1).strip()

        # Determine source from URL or other indicators
        if 'url' in metadata:
            if 'reddit.com' in metadata['url'] or 'redd.it' in metadata['url']:
                metadata['source'] = 'reddit'
            elif 'youtube.com' in metadata['url'] or 'youtu.be' in metadata['url']:
                metadata['source'] = 'youtube'
                # Extract video ID for thumbnail
                video_id_match = re.search(r'(?:v=|youtu\.be/)([a-zA-Z0-9_-]{11})', metadata['url'])
                if video_id_match:
                    metadata['video_id'] = video_id_match.group(1)
            else:
                metadata['source'] = 'unknown'

        return metadata

    def _parse_hidden_metadata(self, hidden_meta_str: str) -> Dict[str, Any]:
        """
        Parse hidden metadata from HTML comment

        Args:
            hidden_meta_str: String like "source=reddit | video_id=abc123 | image_url=https://..."

        Returns:
            Dictionary of metadata fields
        """
        metadata = {}

        # Split by pipe and parse key=value pairs
        pairs = hidden_meta_str.split('|')
        for pair in pairs:
            pair = pair.strip()
            if '=' in pair:
                key, value = pair.split('=', 1)
                metadata[key.strip()] = value.strip()

        return metadata

    def retry_with_fallback(
        self,
        notifier,
        send_method: str,
        report_path: str,
        **kwargs
    ) -> bool:
        """
        Retry notification using parsed report data

        Args:
            notifier: The notifier instance (DiscordNotifier or SynologyNotifier)
            send_method: Name of the send method ('send_rich_report' or 'send_full_report')
            report_path: Path to the report file
            **kwargs: Additional arguments to pass to the send method

        Returns:
            True if retry succeeded, False otherwise
        """
        self.logger.info(f"Attempting fallback retry for {send_method}...")

        for attempt in range(1, self.max_retries + 1):
            try:
                self.logger.info(f"Retry attempt {attempt}/{self.max_retries}")

                # Parse the report
                parsed_items = self.parse_report(report_path)
                if not parsed_items:
                    self.logger.error("Failed to parse report for fallback")
                    return False

                # Wait before retry (with exponential backoff)
                if attempt > 1:
                    delay = self.retry_delay * (2 ** (attempt - 2))
                    self.logger.info(f"Waiting {delay:.1f}s before retry...")
                    time.sleep(delay)

                # Call the appropriate send method
                method = getattr(notifier, send_method)

                if send_method == 'send_rich_report':
                    # Use parsed items for rich report
                    success = method(relevant_contents=parsed_items, **kwargs)
                elif send_method == 'send_full_report':
                    # Use the report file directly for full report
                    success = method(report_path=report_path, **kwargs)
                else:
                    self.logger.error(f"Unknown send method: {send_method}")
                    return False

                if success:
                    self.logger.info(f"Fallback retry succeeded on attempt {attempt}")
                    return True
                else:
                    self.logger.warning(f"Retry attempt {attempt} failed")

            except Exception as e:
                self.logger.error(f"Retry attempt {attempt} raised exception: {e}", exc_info=True)

        self.logger.error(f"All {self.max_retries} retry attempts failed")
        return False

    def find_latest_report(self, date_str: str = None) -> Optional[str]:
        """
        Find the latest report file for this package

        Args:
            date_str: Optional date string (YYYY-MM-DD) to find specific report

        Returns:
            Path to the report file, or None if not found
        """
        if not self.report_dir.exists():
            self.logger.warning(f"Report directory does not exist: {self.report_dir}")
            return None

        # Pattern: <package_name>_report_YYYY-MM-DD.md
        if date_str:
            report_name = f"{self.package_name}_report_{date_str}.md"
            report_path = self.report_dir / report_name
            if report_path.exists():
                return str(report_path)
        else:
            # Find latest report
            pattern = f"{self.package_name}_report_*.md"
            reports = sorted(self.report_dir.glob(pattern), reverse=True)
            if reports:
                return str(reports[0])

        return None


if __name__ == "__main__":
    # Quick test
    import sys
    sys.path.append(str(Path(__file__).parent.parent.parent))

    from src.utils import setup_package_logging

    setup_package_logging("test")

    # Test with existing report
    manager = FallbackManager("ai_trends")

    # Find latest report
    latest = manager.find_latest_report()
    if latest:
        print(f"Found latest report: {latest}")

        # Parse it
        items = manager.parse_report(latest)
        if items:
            print(f"\nParsed {len(items)} items:")
            for i, item in enumerate(items[:2], 1):  # Show first 2
                print(f"\n{i}. {item['title'][:60]}...")
                print(f"   Category: {item['category']}")
                print(f"   Score: {item['relevance_score']}/10")
                print(f"   Metadata: {list(item['metadata'].keys())}")
    else:
        print("No reports found")
