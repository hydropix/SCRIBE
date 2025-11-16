"""Discord webhook notifier for SCRIBE reports"""

import os
import logging
import time
from typing import Dict, Any, Optional, List
from datetime import datetime

import requests


class DiscordNotifier:
    """Sends report summaries to Discord via webhook"""

    # Discord's character limit per message
    MAX_MESSAGE_LENGTH = 2000
    # Delay between messages to avoid rate limiting (in seconds)
    MESSAGE_DELAY = 1.0

    def __init__(self):
        """Initialize Discord notifier with webhook URL from environment"""
        self.logger = logging.getLogger("SCRIBE.DiscordNotifier")
        self.webhook_url = os.getenv('DISCORD_WEBHOOK_URL')

        if not self.webhook_url:
            self.logger.warning("DISCORD_WEBHOOK_URL not set. Discord notifications disabled.")
        else:
            self.logger.info("Discord notifier initialized")

    def send_full_report(self, report_path: str, mention_role: str = "") -> bool:
        """
        Send the complete report content to Discord webhook

        Args:
            report_path: Path to the generated report file
            mention_role: Optional role to mention (e.g., "@everyone")

        Returns:
            True if successful, False otherwise
        """
        if not self.webhook_url:
            self.logger.warning("Cannot send Discord notification: webhook URL not configured")
            return False

        try:
            # Read the full report
            with open(report_path, 'r', encoding='utf-8') as f:
                report_content = f.read()

            # Clean up markdown for Discord (remove triple backticks that might interfere)
            report_content = self._clean_markdown_for_discord(report_content)

            # Add mention at the beginning if specified
            if mention_role:
                report_content = f"{mention_role}\n\n{report_content}"

            # Split into chunks
            message_chunks = self._split_message(report_content)

            self.logger.info(f"Sending full report in {len(message_chunks)} message(s) to Discord")

            # Send each chunk
            for i, chunk in enumerate(message_chunks, 1):
                payload = {
                    "content": chunk
                }

                response = requests.post(
                    self.webhook_url,
                    json=payload,
                    timeout=10
                )

                if response.status_code not in (200, 204):
                    self.logger.error(
                        f"Discord webhook failed on chunk {i}/{len(message_chunks)} "
                        f"with status {response.status_code}: {response.text}"
                    )
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
            self.logger.error("Discord webhook request timed out")
            return False
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Discord webhook request failed: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error sending Discord notification: {e}")
            return False

    def _clean_markdown_for_discord(self, content: str) -> str:
        """
        Clean up markdown content for better Discord rendering

        Args:
            content: Raw markdown content

        Returns:
            Cleaned content suitable for Discord
        """
        # Remove code block markers that might cause issues
        # Keep the content but remove ```markdown blocks
        import re

        # Replace ```markdown ... ``` blocks with just the content
        content = re.sub(r'```markdown\n(.*?)\n```', r'\1', content, flags=re.DOTALL)

        # Convert Markdown links to Discord format
        # Discord doesn't support [text](url) syntax, URLs should be plain text
        content = self._convert_markdown_links_to_discord(content)

        # Remove other code blocks but keep content (optional, can be adjusted)
        # content = re.sub(r'```\n(.*?)\n```', r'\1', content, flags=re.DOTALL)

        return content

    def _convert_markdown_links_to_discord(self, content: str) -> str:
        """
        Convert Markdown links to Discord-friendly format

        Discord auto-embeds URLs, so we convert:
        - [text](url) -> text: <url> (if text != url)
        - [url](url) or [url] -> <url> (just the URL with angle brackets)

        Args:
            content: Content with Markdown links

        Returns:
            Content with Discord-friendly links
        """
        import re

        # Pattern for Markdown links: [text](url)
        # This handles both [title](url) and [url](url) cases
        def replace_markdown_link(match):
            text = match.group(1).strip()
            url = match.group(2).strip()

            # Remove any surrounding brackets from the text if present
            text = text.strip('[]')

            # If text is the same as URL (or very similar), just show the URL
            if text == url or text.replace('https://', '').replace('http://', '') == url.replace('https://', '').replace('http://', ''):
                return f"<{url}>"

            # If text is meaningful, show both text and URL
            return f"{text}: <{url}>"

        # Match [text](url) pattern
        content = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', replace_markdown_link, content)

        # Also handle bare URLs in brackets like [https://...]
        # Convert [url] to <url>
        content = re.sub(r'\[(https?://[^\]]+)\]', r'<\1>', content)

        return content

    def _split_message(self, message: str) -> List[str]:
        """
        Split a long message into multiple chunks that fit Discord's character limit

        Args:
            message: Original message to split

        Returns:
            List of message chunks, each within Discord's limit
        """
        if len(message) <= self.MAX_MESSAGE_LENGTH:
            return [message]

        chunks = []
        remaining = message
        part_number = 1

        while remaining:
            # Calculate space needed for part indicator
            # We'll add it at the end: "\n\n--- Part X/Y ---"
            # But we don't know total parts yet, so reserve generous space
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

    def _truncate_message(self, message: str) -> str:
        """
        Truncate message to fit Discord's 2000 character limit
        (Legacy method, kept for backward compatibility)

        Args:
            message: Original message

        Returns:
            Truncated message within limit
        """
        max_length = 2000
        truncation_notice = "\n\n*[Message truncated due to length]*"

        if len(message) <= max_length:
            return message

        # Reserve space for truncation notice
        available_length = max_length - len(truncation_notice)

        # Try to truncate at a line break
        truncated = message[:available_length]
        last_newline = truncated.rfind('\n')

        if last_newline > available_length * 0.7:  # Don't cut too much
            truncated = truncated[:last_newline]

        return truncated + truncation_notice
