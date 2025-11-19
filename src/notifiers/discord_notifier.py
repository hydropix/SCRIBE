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
    # Discord embed description limit
    MAX_EMBED_DESCRIPTION = 4096
    # Delay between messages to avoid rate limiting (in seconds)
    MESSAGE_DELAY = 1.0
    # Maximum embeds per message
    MAX_EMBEDS_PER_MESSAGE = 10

    def __init__(self, config: dict):
        """
        Initialize Discord notifier.

        Args:
            config: Discord configuration from package settings
        """
        self.logger = logging.getLogger("SCRIBE.DiscordNotifier")
        self.config = config

        # Get webhook from config env var reference
        webhook_env = config.get('webhook_env', 'DISCORD_WEBHOOK_URL')
        self.webhook_url = os.getenv(webhook_env)

        summary_config = config.get('summary', {})
        summary_env = summary_config.get('webhook_env', 'DISCORD_SUMMARY_WEBHOOK_URL')
        self.summary_webhook_url = os.getenv(summary_env)

        # Get additional config options
        self.rich_embeds = config.get('rich_embeds', True)
        self.max_length = config.get('max_length', 1900)

        if not self.webhook_url:
            self.logger.warning("Discord webhook URL not configured. Discord notifications disabled.")
        else:
            self.logger.info("Discord notifier initialized")

        if self.summary_webhook_url:
            self.logger.info("Discord summary webhook configured")

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

    def send_rich_report(self, relevant_contents: List[Dict[str, Any]], mention_role: str = "") -> bool:
        """
        Send report as rich embeds with images to Discord

        Args:
            relevant_contents: List of analyzed content items with metadata
            mention_role: Optional role to mention (e.g., "@everyone")

        Returns:
            True if successful, False otherwise
        """
        if not self.webhook_url:
            self.logger.warning("Cannot send Discord notification: webhook URL not configured")
            return False

        if not relevant_contents:
            self.logger.warning("No contents to send")
            return False

        try:
            # Send header message first
            header_message = self._create_header_message(len(relevant_contents), mention_role)
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

            # Send embeds for each category
            for category, contents in by_category.items():
                # Send embeds in batches (Discord allows max 10 embeds per message)
                embeds_batch = []
                for content in contents:
                    embed = self._create_content_embed(content, category)
                    embeds_batch.append(embed)

                    # Send batch when full or at end
                    if len(embeds_batch) >= self.MAX_EMBEDS_PER_MESSAGE:
                        if not self._send_embeds(embeds_batch):
                            self.logger.warning(f"Failed to send embeds batch for {category}")
                        embeds_batch = []
                        time.sleep(self.MESSAGE_DELAY)

                # Send remaining embeds
                if embeds_batch:
                    if not self._send_embeds(embeds_batch):
                        self.logger.warning(f"Failed to send final embeds batch for {category}")
                    time.sleep(self.MESSAGE_DELAY)

            # Send footer
            footer_message = f"---\n*Report generated by SCRIBE - {len(relevant_contents)} insights total*"
            self._send_message(footer_message)

            self.logger.info(f"Rich report sent successfully ({len(relevant_contents)} items)")
            return True

        except requests.exceptions.Timeout:
            self.logger.error("Discord webhook request timed out")
            return False
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Discord webhook request failed: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error sending Discord notification: {e}")
            return False

    def _create_header_message(self, total_insights: int, mention_role: str = "") -> str:
        """Create the header message for the report"""
        current_datetime = datetime.now()
        formatted_date = current_datetime.strftime('%d %B %Y')
        formatted_time = current_datetime.strftime('%H:%M')

        header = f"# AI TRENDS & INNOVATIONS\n\n---\n\n## {formatted_date} | {formatted_time}\n\n---"

        if mention_role:
            header = f"{mention_role}\n\n{header}"

        return header

    def _create_content_embed(self, content: Dict[str, Any], category: str = None) -> Dict[str, Any]:
        """
        Create a Discord embed for a content item

        Args:
            content: Analyzed content item with metadata
            category: Category name to display in the embed

        Returns:
            Discord embed dictionary
        """
        # Use provided category or get from content
        display_category = category or content.get('category', 'Other')

        # Get display title
        display_title = content.get('translated_title', content.get('title', 'Untitled'))

        # Truncate title if too long (Discord limit is 256)
        if len(display_title) > 256:
            display_title = display_title[:253] + "..."

        # Build description
        description_parts = []

        # Category tag at the top
        description_parts.append(f"**📁 {display_category}**\n")

        # Hook (teaser)
        if content.get('hook'):
            description_parts.append(f"*{content['hook']}*\n")

        # Insights (main content)
        if content.get('insights'):
            insights_text = content['insights']
            # Truncate if too long
            max_insights_length = self.MAX_EMBED_DESCRIPTION - 600  # Leave room for other parts including category
            if len(insights_text) > max_insights_length:
                insights_text = insights_text[:max_insights_length] + "..."
            description_parts.append(insights_text)

        description = "\n".join(description_parts)

        # Create base embed
        embed = {
            "title": display_title,
            "description": description,
            "color": self._get_category_color(display_category),
            "timestamp": datetime.utcnow().isoformat()
        }

        # Add URL if available
        metadata = content.get('metadata', {})
        url = metadata.get('permalink') or metadata.get('url')
        if url:
            embed["url"] = url

        # Add image if available (Reddit posts)
        image_url = metadata.get('image_url')
        if image_url:
            embed["image"] = {"url": image_url}

        # Add thumbnail for YouTube (video thumbnail)
        if metadata.get('source') == 'youtube' and metadata.get('video_id'):
            thumbnail_url = f"https://img.youtube.com/vi/{metadata['video_id']}/maxresdefault.jpg"
            embed["thumbnail"] = {"url": thumbnail_url}

        # Add footer with metadata
        footer_parts = []
        score = content.get('relevance_score', 0)
        footer_parts.append(f"Relevance: {score}/10")

        if metadata.get('author'):
            footer_parts.append(f"Author: {metadata['author']}")
        elif metadata.get('channel_title'):
            footer_parts.append(f"Channel: {metadata['channel_title']}")

        if metadata.get('subreddit'):
            footer_parts.append(f"r/{metadata['subreddit']}")

        embed["footer"] = {"text": " | ".join(footer_parts)}

        # Add author field for source
        source = metadata.get('source', 'unknown')
        if source == 'reddit':
            embed["author"] = {
                "name": "Reddit",
                "icon_url": "https://www.redditstatic.com/desktop2x/img/favicon/android-icon-192x192.png"
            }
        elif source == 'youtube':
            embed["author"] = {
                "name": "YouTube",
                "icon_url": "https://www.youtube.com/s/desktop/f506bd45/img/favicon_144x144.png"
            }

        return embed

    def _get_category_color(self, category: str) -> int:
        """
        Get Discord embed color based on category

        Args:
            category: Content category

        Returns:
            Color as integer (Discord format)
        """
        # Color mapping for different categories
        colors = {
            "Large Language Models": 0x5865F2,  # Discord blurple
            "Computer Vision": 0x57F287,  # Green
            "Robotics": 0xFEE75C,  # Yellow
            "Machine Learning": 0xEB459E,  # Pink
            "Deep Learning": 0xED4245,  # Red
            "Natural Language Processing": 0x3498DB,  # Blue
            "Reinforcement Learning": 0xE67E22,  # Orange
            "Generative AI": 0x9B59B6,  # Purple
            "AI Ethics": 0x1ABC9C,  # Teal
            "AI Research": 0x95A5A6,  # Gray
        }
        return colors.get(category, 0x99AAB5)  # Default gray

    def _send_message(self, content: str) -> bool:
        """
        Send a simple text message to Discord

        Args:
            content: Message content

        Returns:
            True if successful
        """
        try:
            payload = {"content": content}
            response = requests.post(self.webhook_url, json=payload, timeout=10)
            return response.status_code in (200, 204)
        except Exception as e:
            self.logger.error(f"Failed to send message: {e}")
            return False

    def _send_embeds(self, embeds: List[Dict[str, Any]]) -> bool:
        """
        Send embeds to Discord

        Args:
            embeds: List of embed dictionaries

        Returns:
            True if successful
        """
        try:
            payload = {"embeds": embeds}
            response = requests.post(self.webhook_url, json=payload, timeout=10)
            if response.status_code not in (200, 204):
                self.logger.error(f"Failed to send embeds: {response.status_code} - {response.text}")
                return False
            return True
        except Exception as e:
            self.logger.error(f"Failed to send embeds: {e}")
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

    def send_summary(self, summary_text: str, mention_role: str = "") -> bool:
        """
        Send a daily summary to the summary webhook (separate channel)
        Uses message splitting if content exceeds 2000 chars

        Args:
            summary_text: The summary text (can exceed 2000 chars, will be split)
            mention_role: Optional role to mention (e.g., "@everyone")

        Returns:
            True if successful, False otherwise
        """
        if not self.summary_webhook_url:
            self.logger.warning("Cannot send summary: DISCORD_SUMMARY_WEBHOOK_URL not configured")
            return False

        try:
            # Add mention at the beginning if specified
            content = f"{mention_role}\n\n{summary_text}" if mention_role else summary_text

            # Split into chunks if necessary (same as full report)
            message_chunks = self._split_message(content)

            self.logger.info(f"Sending summary in {len(message_chunks)} message(s) to Discord")

            # Send each chunk
            for i, chunk in enumerate(message_chunks, 1):
                payload = {"content": chunk}

                response = requests.post(
                    self.summary_webhook_url,
                    json=payload,
                    timeout=10
                )

                if response.status_code not in (200, 204):
                    self.logger.error(
                        f"Summary webhook failed on chunk {i}/{len(message_chunks)} "
                        f"with status {response.status_code}: {response.text}"
                    )
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
