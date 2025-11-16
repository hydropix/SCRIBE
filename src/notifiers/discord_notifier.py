"""Discord webhook notifier for SCRIBE reports"""

import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime

import requests


class DiscordNotifier:
    """Sends report summaries to Discord via webhook"""

    def __init__(self):
        """Initialize Discord notifier with webhook URL from environment"""
        self.logger = logging.getLogger("SCRIBE.DiscordNotifier")
        self.webhook_url = os.getenv('DISCORD_WEBHOOK_URL')

        if not self.webhook_url:
            self.logger.warning("DISCORD_WEBHOOK_URL not set. Discord notifications disabled.")
        else:
            self.logger.info("Discord notifier initialized")

    def send_report_summary(
        self,
        report_path: str,
        executive_summary: str,
        metrics: Dict[str, Any],
        mention_role: str = ""
    ) -> bool:
        """
        Send report summary to Discord webhook

        Args:
            report_path: Path to the generated report
            executive_summary: Executive summary text (3-5 sentences)
            metrics: Dictionary containing report metrics
            mention_role: Optional role to mention (e.g., "@everyone")

        Returns:
            True if successful, False otherwise
        """
        if not self.webhook_url:
            self.logger.warning("Cannot send Discord notification: webhook URL not configured")
            return False

        try:
            message = self._format_message(report_path, executive_summary, metrics, mention_role)

            # Ensure message respects Discord's 2000 character limit
            if len(message) > 2000:
                self.logger.warning(f"Message too long ({len(message)} chars), truncating...")
                message = self._truncate_message(message)

            payload = {
                "content": message
            }

            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10
            )

            if response.status_code in (200, 204):
                self.logger.info("Discord notification sent successfully")
                return True
            else:
                self.logger.error(
                    f"Discord webhook failed with status {response.status_code}: {response.text}"
                )
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

    def _format_message(
        self,
        report_path: str,
        executive_summary: str,
        metrics: Dict[str, Any],
        mention_role: str = ""
    ) -> str:
        """
        Format the Discord message with report summary and metrics

        Args:
            report_path: Path to the generated report
            executive_summary: Executive summary text
            metrics: Dictionary containing report metrics
            mention_role: Optional role to mention

        Returns:
            Formatted message string
        """
        # Extract date from report path or use current date
        report_date = datetime.now().strftime('%Y-%m-%d')
        if report_path:
            # Try to extract date from filename (e.g., veille_ia_2024-01-15.md)
            import re
            date_match = re.search(r'(\d{4}-\d{2}-\d{2})', report_path)
            if date_match:
                report_date = date_match.group(1)

        lines = []

        # Add mention if specified
        if mention_role:
            lines.append(mention_role)
            lines.append("")

        # Title
        lines.append(f"**SCRIBE Intelligence Report - {report_date}**")
        lines.append("")

        # Executive Summary
        lines.append("**Executive Summary**")
        lines.append(executive_summary.strip())
        lines.append("")

        # Key Metrics
        lines.append("**Key Metrics**")

        if metrics:
            total_analyzed = metrics.get('total_analyzed', 0)
            relevant_count = metrics.get('relevant_count', 0)
            relevant_percentage = metrics.get('relevant_percentage', 0)
            average_score = metrics.get('average_score', 0)

            lines.append(f"- Total analyzed: {total_analyzed}")
            lines.append(f"- Relevant: {relevant_count} ({relevant_percentage:.1f}%)")
            lines.append(f"- Avg relevance score: {average_score:.1f}/10")

            # Sources breakdown
            if 'by_source' in metrics:
                sources = []
                for source, count in metrics['by_source'].items():
                    sources.append(f"{source.title()}: {count}")
                if sources:
                    lines.append(f"- Sources: {', '.join(sources)}")

            # Categories count
            if 'categories_distribution' in metrics:
                num_categories = len(metrics['categories_distribution'])
                lines.append(f"- Categories covered: {num_categories}")
        else:
            lines.append("- No metrics available")

        lines.append("")
        lines.append(f"*Report saved: `{report_path}`*")

        return "\n".join(lines)

    def _truncate_message(self, message: str) -> str:
        """
        Truncate message to fit Discord's 2000 character limit

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
