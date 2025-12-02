"""Synology Chat webhook notifier for SCRIBE reports"""

import os
import logging
import time
from typing import Dict, Any, List
from datetime import datetime
from urllib.parse import urlencode

import requests


class SynologyNotifier:
    """Sends report summaries to Synology Chat via webhook"""

    # Synology Chat's character limit per message (similar to Discord)
    MAX_MESSAGE_LENGTH = 2000
    # Delay between messages to avoid rate limiting (in seconds)
    MESSAGE_DELAY = 1.0

    def __init__(self, config: dict, package_display_name: str = "AI Trends & Innovations"):
        """
        Initialize Synology Chat notifier.

        Args:
            config: Synology Chat configuration from package settings
            package_display_name: Display name of the package for report header
        """
        self.logger = logging.getLogger("SCRIBE.SynologyNotifier")
        self.config = config
        self.package_display_name = package_display_name

        # Get webhook URL from config env var reference
        webhook_env = config.get('webhook_env', 'SYNOLOGY_WEBHOOK_URL')
        self.webhook_url = os.getenv(webhook_env)

        # Get summary webhook URL (optional separate channel)
        summary_config = config.get('summary', {})
        summary_env = summary_config.get('webhook_env', 'SYNOLOGY_SUMMARY_WEBHOOK_URL')
        self.summary_webhook_url = os.getenv(summary_env)

        # Get additional config options
        self.max_length = config.get('max_length', 1900)

        if not self.webhook_url:
            self.logger.warning("Synology Chat webhook URL not configured. Synology notifications disabled.")
        else:
            self.logger.info("Synology Chat notifier initialized")

        if self.summary_webhook_url:
            self.logger.info("Synology Chat summary webhook configured")

    def send_full_report(self, report_path: str, mention: str = "") -> bool:
        """
        Send the complete report content to Synology Chat webhook

        Args:
            report_path: Path to the generated report file
            mention: Optional mention text (e.g., "@all")

        Returns:
            True if successful, False otherwise
        """
        if not self.webhook_url:
            self.logger.warning("Cannot send Synology notification: webhook URL not configured")
            return False

        try:
            # Read the full report
            with open(report_path, 'r', encoding='utf-8') as f:
                report_content = f.read()

            # Add mention at the beginning if specified
            if mention:
                report_content = f"{mention}\n\n{report_content}"

            # Split into chunks
            message_chunks = self._split_message(report_content)

            self.logger.info(f"Sending full report in {len(message_chunks)} message(s) to Synology Chat")

            # Send each chunk
            for i, chunk in enumerate(message_chunks, 1):
                if not self._send_message(chunk):
                    self.logger.error(f"Failed to send chunk {i}/{len(message_chunks)}")
                    return False

                self.logger.info(f"Sent part {i}/{len(message_chunks)}")

                # Add delay between messages to avoid rate limiting
                if i < len(message_chunks):
                    time.sleep(self.MESSAGE_DELAY)

            self.logger.info(f"Full report sent successfully ({len(message_chunks)} part(s))")
            return True

        except FileNotFoundError:
            self.logger.error(f"Report file not found: {report_path}")
            return False
        except requests.exceptions.Timeout:
            self.logger.error("Synology Chat webhook request timed out")
            return False
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Synology Chat webhook request failed: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error sending Synology notification: {e}")
            return False

    def send_rich_report(self, relevant_contents: List[Dict[str, Any]], mention: str = "") -> bool:
        """
        Send report as formatted messages to Synology Chat
        Note: Synology Chat doesn't support rich embeds like Discord,
        so we format content as structured text messages

        Args:
            relevant_contents: List of analyzed content items with metadata
            mention: Optional mention text (e.g., "@all")

        Returns:
            True if successful, False otherwise
        """
        if not self.webhook_url:
            self.logger.warning("Cannot send Synology notification: webhook URL not configured")
            return False

        if not relevant_contents:
            self.logger.warning("No contents to send")
            return False

        try:
            # Send header message first
            header_message = self._create_header_message(len(relevant_contents), mention)
            if not self._send_message(header_message):
                return False

            time.sleep(self.MESSAGE_DELAY)

            # Group contents by category for organized display
            by_category = {}
            for content in relevant_contents:
                category = content.get('category', 'Other')
                if category not in by_category:
                    by_category[category] = []
                by_category[category].append(content)

            # Send formatted messages for each category
            for category, contents in by_category.items():
                for content in contents:
                    message = self._create_content_message(content, category)
                    if not self._send_message(message):
                        self.logger.warning(f"Failed to send content message for {category}")
                    time.sleep(self.MESSAGE_DELAY)

            # Send footer
            footer_message = f"---\nReport generated by SCRIBE - {len(relevant_contents)} insights total"
            self._send_message(footer_message)

            self.logger.info(f"Rich report sent successfully ({len(relevant_contents)} items)")
            return True

        except requests.exceptions.Timeout:
            self.logger.error("Synology Chat webhook request timed out")
            return False
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Synology Chat webhook request failed: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error sending Synology notification: {e}")
            return False

    def _create_header_message(self, total_insights: int, mention: str = "") -> str:
        """Create the header message for the report"""
        current_datetime = datetime.now()
        formatted_date = current_datetime.strftime('%d %B %Y')
        formatted_time = current_datetime.strftime('%H:%M')

        header = f"# {self.package_display_name.upper()}\n\n---\n\n## {formatted_date} | {formatted_time}\n\n---"

        if mention:
            header = f"{mention}\n\n{header}"

        return header

    def _create_content_message(self, content: Dict[str, Any], category: str = None) -> str:
        """
        Create a formatted text message for a content item
        (Synology Chat doesn't support rich embeds, so we use formatted text)

        Args:
            content: Analyzed content item with metadata
            category: Category name to display

        Returns:
            Formatted message string
        """
        # Use provided category or get from content
        display_category = category or content.get('category', 'Other')

        # Get display title
        display_title = content.get('translated_title', content.get('title', 'Untitled'))

        # Build message parts
        message_parts = []

        # Title and category
        message_parts.append(f"**{display_title}**")
        message_parts.append(f"📁 Category: {display_category}")

        # Hook (teaser)
        if content.get('hook'):
            message_parts.append(f"\n*{content['hook']}*")

        # Insights (main content)
        if content.get('insights'):
            message_parts.append(f"\n{content['insights']}")

        # Metadata
        metadata = content.get('metadata', {})
        meta_parts = []

        score = content.get('relevance_score', 0)
        meta_parts.append(f"Score: {score}")

        if metadata.get('author'):
            meta_parts.append(f"Author: {metadata['author']}")
        elif metadata.get('channel_title'):
            meta_parts.append(f"Channel: {metadata['channel_title']}")

        if metadata.get('subreddit'):
            meta_parts.append(f"r/{metadata['subreddit']}")

        source = metadata.get('source', 'unknown')
        if source == 'reddit':
            meta_parts.append("Source: Reddit")
        elif source == 'youtube':
            meta_parts.append("Source: YouTube")

        message_parts.append(f"\n{' | '.join(meta_parts)}")

        # Add URL if available
        url = metadata.get('permalink') or metadata.get('url')
        if url:
            message_parts.append(f"\n🔗 {url}")

        # Add separator
        message_parts.append("\n" + "-" * 50)

        return "\n".join(message_parts)

    def _send_message(self, text: str, file_url: str = None) -> bool:
        """
        Send a message to Synology Chat using the webhook

        Args:
            text: Message text
            file_url: Optional file URL to attach

        Returns:
            True if successful
        """
        try:
            # Prepare payload according to Synology Chat API
            payload = {"text": text}

            if file_url:
                payload["file_url"] = file_url

            # Synology Chat expects the payload to be URL-encoded
            # and sent as the value of the 'payload' parameter
            data = urlencode({"payload": str(payload).replace("'", '"')})

            response = requests.post(
                self.webhook_url,
                data=data,
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                timeout=10
            )

            if response.status_code not in (200, 204):
                self.logger.error(f"Synology webhook failed with status {response.status_code}: {response.text}")
                return False

            return True

        except Exception as e:
            self.logger.error(f"Failed to send message to Synology Chat: {e}")
            return False

    def _split_message(self, message: str) -> List[str]:
        """
        Split a long message into multiple chunks that fit Synology Chat's character limit

        Args:
            message: Original message to split

        Returns:
            List of message chunks, each within the limit
        """
        if len(message) <= self.MAX_MESSAGE_LENGTH:
            return [message]

        chunks = []
        remaining = message
        part_number = 1

        while remaining:
            # Calculate space needed for part indicator
            part_indicator_space = 30

            max_chunk_size = self.MAX_MESSAGE_LENGTH - part_indicator_space

            if len(remaining) <= max_chunk_size:
                # Last chunk
                chunks.append(remaining)
                break

            # Find a good split point
            chunk = remaining[:max_chunk_size]
            split_point = max_chunk_size

            # Try to split at paragraph break (double newline)
            last_paragraph = chunk.rfind('\n\n')
            if last_paragraph > max_chunk_size * 0.5:
                split_point = last_paragraph + 2
            else:
                # Try to split at single newline
                last_newline = chunk.rfind('\n')
                if last_newline > max_chunk_size * 0.7:
                    split_point = last_newline + 1
                else:
                    # Try to split at space
                    last_space = chunk.rfind(' ')
                    if last_space > max_chunk_size * 0.8:
                        split_point = last_space + 1

            chunk = remaining[:split_point].rstrip()
            chunks.append(chunk)
            remaining = remaining[split_point:].lstrip()
            part_number += 1

        # Add part indicators if we have multiple chunks
        if len(chunks) > 1:
            total_parts = len(chunks)
            for i in range(len(chunks)):
                part_indicator = f"\n\n--- Part {i + 1}/{total_parts} ---"
                chunks[i] = chunks[i] + part_indicator

        return chunks

    def send_summary(self, summary_text: str, mention: str = "") -> bool:
        """
        Send a daily summary to the summary webhook (separate channel)
        Uses message splitting if content exceeds character limit

        Args:
            summary_text: The summary text (can exceed limit, will be split)
            mention: Optional mention text (e.g., "@all")

        Returns:
            True if successful, False otherwise
        """
        if not self.summary_webhook_url:
            self.logger.warning("Cannot send summary: Synology summary webhook URL not configured")
            return False

        try:
            # Add mention at the beginning if specified
            content = f"{mention}\n\n{summary_text}" if mention else summary_text

            # Split into chunks if necessary
            message_chunks = self._split_message(content)

            self.logger.info(f"Sending summary in {len(message_chunks)} message(s) to Synology Chat")

            # Send each chunk
            for i, chunk in enumerate(message_chunks, 1):
                if not self._send_message(chunk):
                    self.logger.error(f"Failed to send summary chunk {i}/{len(message_chunks)}")
                    return False

                self.logger.info(f"Sent summary part {i}/{len(message_chunks)}")

                # Add delay between messages to avoid rate limiting
                if i < len(message_chunks):
                    time.sleep(self.MESSAGE_DELAY)

            self.logger.info(f"Summary sent successfully ({len(summary_text)} chars, {len(message_chunks)} part(s))")
            return True

        except requests.exceptions.Timeout:
            self.logger.error("Summary webhook request timed out")
            return False
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Summary webhook request failed: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error sending summary: {e}")
            return False
