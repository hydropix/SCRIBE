#!/usr/bin/env python3
"""
SCRIBE - Source Content Retrieval and Intelligence Bot Engine

Multi-package intelligence gathering system.
"""

import argparse
import logging
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

from src.package_manager import PackageManager, PackageConfig
from src.utils import (
    setup_package_logging,
    load_env_variables,
    save_package_raw_data_log,
    get_package_raw_logs_dir
)
from src.collectors.reddit_collector import RedditCollector
from src.collectors.youtube_collector import YouTubeCollector
from src.processors.content_analyzer import ContentAnalyzer
from src.processors.deduplicator import ContentDeduplicator
from src.processors.nli_prefilter import NLIPrefilter
from src.storage.cache_manager import CacheManager
from src.storage.report_generator import ReportGenerator
from src.notifiers.discord_notifier import DiscordNotifier
from src.notifiers.synology_notifier import SynologyNotifier
from src.notifiers.fallback_manager import FallbackManager


def ensure_ollama_running(host: str = "http://localhost:11434", timeout: int = 30) -> bool:
    """
    Check if Ollama is running and start it if not.

    Args:
        host: Ollama API host URL
        timeout: Maximum time to wait for Ollama to start (seconds)

    Returns:
        True if Ollama is running, False if it couldn't be started
    """
    logger = logging.getLogger(__name__)

    # Check if Ollama is already running
    try:
        response = requests.get(f"{host}/api/tags", timeout=5)
        if response.status_code == 200:
            logger.info("Ollama is already running")
            return True
    except requests.exceptions.RequestException:
        pass

    # Ollama not running, try to start it
    logger.info("Ollama is not running. Attempting to start...")

    try:
        # Start Ollama in background (Windows-compatible)
        if sys.platform == "win32":
            subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
        else:
            subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
    except FileNotFoundError:
        logger.error("Ollama executable not found. Please install Ollama first.")
        return False
    except Exception as e:
        logger.error(f"Failed to start Ollama: {e}")
        return False

    # Wait for Ollama to be ready
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"{host}/api/tags", timeout=2)
            if response.status_code == 200:
                logger.info(f"Ollama started successfully (took {time.time() - start_time:.1f}s)")
                return True
        except requests.exceptions.RequestException:
            pass
        time.sleep(1)

    logger.error(f"Ollama failed to start within {timeout} seconds")
    return False


class SCRIBE:
    """Main orchestrator for SCRIBE intelligence gathering."""

    def __init__(self, package_name: str, language: str = None):
        """
        Initialize SCRIBE.

        Args:
            package_name: Name of the package to run
            language: Override language for reports
        """
        self.package_manager = PackageManager()
        self.package_config = self.package_manager.load_package(package_name)
        self.config = self.package_config.settings
        self._init_package_mode(language)

    def _init_package_mode(self, language: str = None):
        """Initialize components in package mode."""
        pkg = self.package_config

        # Setup package-specific logging
        self.logger = setup_package_logging(pkg.name)
        self.logger.info("=" * 60)
        self.logger.info(f"SCRIBE - {pkg.display_name}")
        self.logger.info("=" * 60)

        # Load environment variables
        try:
            load_env_variables()
        except FileNotFoundError as e:
            self.logger.error(str(e))
            raise

        # Determine language
        language_map = {
            'en': 'English',
            'fr': 'French',
            'es': 'Spanish',
            'de': 'German',
            'it': 'Italian',
            'pt': 'Portuguese',
            'nl': 'Dutch',
            'ru': 'Russian',
            'zh': 'Chinese',
            'ja': 'Japanese',
            'ar': 'Arabic'
        }

        if language:
            language_full = language_map.get(language, language)
        else:
            lang_code = pkg.settings.get('reports', {}).get('language', 'fr')
            language_full = language_map.get(lang_code, 'French')

        self.language = language_full
        self.logger.info(f"Initializing components (language: {language_full})...")

        # Initialize collectors with package config
        self.reddit_collector = RedditCollector(config=pkg.settings)

        # Only initialize YouTube collector if enabled
        youtube_enabled = pkg.settings.get('youtube', {}).get('enabled', True)
        self.youtube_collector = YouTubeCollector(config=pkg.settings) if youtube_enabled else None

        # Initialize processors with package config
        self.analyzer = ContentAnalyzer(
            config=pkg.settings,
            prompts=pkg.prompts,
            ollama_config=pkg.get_ollama_config(),
            language=language_full
        )
        self.deduplicator = ContentDeduplicator(
            tfidf_threshold=pkg.settings.get('analysis', {}).get('tfidf_threshold', 0.67),
            simhash_threshold=pkg.settings.get('analysis', {}).get('simhash_threshold', 0.85)
        )

        # Initialize NLI pre-filter (fast filtering before LLM)
        nli_config = pkg.settings.get('nli_prefilter', {})
        self.nli_prefilter = NLIPrefilter(
            model_name=nli_config.get('model', 'facebook/bart-large-mnli'),
            relevance_labels=nli_config.get('relevance_labels'),
            threshold=nli_config.get('threshold', 0.5),
            enabled=nli_config.get('enabled', False),
            max_text_length=nli_config.get('max_text_length', 512),
            device=nli_config.get('device', 'cpu')
        )

        # Initialize storage with package-specific paths
        self.cache = CacheManager(
            db_path=str(pkg.cache_path),
            retention_days=pkg.settings.get('cache', {}).get('retention_days', 90)
        )
        self.report_generator = ReportGenerator(
            package_name=pkg.name,
            config=pkg.settings,
            prompts=pkg.prompts,
            ollama_config=pkg.get_ollama_config(),
            language=language_full,
            package_display_name=pkg.display_name
        )

        # Initialize notifiers with package config
        discord_config = pkg.settings.get('discord', {})
        self.discord_notifier = DiscordNotifier(
            config=discord_config,
            package_display_name=pkg.display_name
        )

        synology_config = pkg.settings.get('synology', {})
        self.synology_notifier = SynologyNotifier(
            config=synology_config,
            package_display_name=pkg.display_name
        )

        # Initialize fallback manager for retry mechanism
        fallback_config = pkg.settings.get('fallback', {})
        self.fallback_manager = FallbackManager(
            package_name=pkg.name,
            max_retries=fallback_config.get('max_retries', 3),
            retry_delay=fallback_config.get('retry_delay', 5.0)
        )

        self.logger.info("All components initialized successfully")

    def run_veille(self):
        """Execute a complete intelligence gathering cycle."""
        pkg_name = self.package_config.name

        self.logger.info("\n" + "=" * 60)
        self.logger.info(f"Starting intelligence cycle at {datetime.now()}")
        self.logger.info("=" * 60 + "\n")

        # Ensure Ollama is running before starting the cycle
        ollama_host = self.package_config.get_ollama_config().get('host', 'http://localhost:11434')
        if not ensure_ollama_running(host=ollama_host):
            self.logger.error("Cannot proceed without Ollama. Exiting.")
            return

        # 0. Cache cleanup (remove entries older than retention period)
        self.logger.info("STEP 0: Cleaning up old cache entries...")
        retention_days = self.config.get('cache', {}).get('retention_days', 90)
        self.cache.cleanup_old_entries(days_to_keep=retention_days)

        # 0.5 Clear previous raw data logs
        self.logger.info("Clearing previous raw data logs...")
        raw_logs_dir = get_package_raw_logs_dir(self.package_config.name)
        if raw_logs_dir.exists():
            for file in raw_logs_dir.glob("*.md"):
                file.unlink()

        # 1. Data collection
        self.logger.info("\nSTEP 1: Collecting data from sources...")

        reddit_posts = self._collect_reddit()
        youtube_videos = self._collect_youtube()

        # Save raw data to markdown logs
        if reddit_posts:
            reddit_log_path = save_package_raw_data_log(
                self.package_config.name, reddit_posts, 'reddit'
            )
            self.logger.info(f"Raw Reddit data saved to: {reddit_log_path}")

        if youtube_videos:
            youtube_log_path = save_package_raw_data_log(
                self.package_config.name, youtube_videos, 'youtube'
            )
            self.logger.info(f"Raw YouTube data saved to: {youtube_log_path}")

        total_collected = len(reddit_posts) + len(youtube_videos)
        self.logger.info(f"Total collected: {total_collected} items")

        if total_collected == 0:
            self.logger.warning("No new content collected. Exiting.")
            return

        # 2. Content preparation for analysis
        self.logger.info("\nSTEP 2: Preparing contents for analysis...")

        all_contents = self._prepare_contents(reddit_posts, youtube_videos)

        # Filter already processed contents
        unprocessed = self.cache.filter_unprocessed(all_contents)

        self.logger.info(f"Unprocessed contents: {len(unprocessed)}")

        if not unprocessed:
            self.logger.info("All contents already processed. Exiting.")
            return

        # 2.5 NLI Pre-filtering (fast filter before LLM)
        nli_config = self.config.get('nli_prefilter', {})
        nli_filtered_out = []

        if nli_config.get('enabled', False):
            self.logger.info("\nSTEP 2.5: NLI pre-filtering (fast relevance check)...")

            unprocessed, nli_filtered_out = self.nli_prefilter.filter_batch(
                unprocessed,
                content_key='text',
                title_key='title'
            )

            if nli_filtered_out:
                nli_stats = self.nli_prefilter.get_statistics(nli_filtered_out)
                self.logger.info(
                    f"NLI filtered out {nli_stats['filtered_count']} items "
                    f"(avg score: {nli_stats['avg_score']:.2f})"
                )

            if not unprocessed:
                self.logger.info("All contents filtered by NLI pre-filter. No LLM analysis needed.")
                return

        # 3. LLM analysis
        self.logger.info("\nSTEP 3: Analyzing contents with LLM...")

        analyzed = self.analyzer.batch_analyze(
            unprocessed,
            content_key='text',
            title_key='title'
        )

        # Mark as processed in cache
        self.cache.batch_mark_processed(analyzed)

        # 4. Filter relevant contents
        self.logger.info("\nSTEP 4: Filtering relevant contents...")

        relevant = self.analyzer.filter_relevant(analyzed)

        self.logger.info(f"Relevant contents: {len(relevant)}")

        if not relevant:
            self.logger.info("No relevant content found. No report will be generated.")
            return

        # 5. Deduplication
        self.logger.info("\nSTEP 5: Deduplicating contents...")

        unique = self.deduplicator.deduplicate(relevant)

        self.logger.info(f"Unique relevant contents: {len(unique)}")

        # Check minimum threshold to generate a report
        min_insights = self.config.get('reports', {}).get('min_insights', 3)

        if len(unique) < min_insights:
            self.logger.info(
                f"Only {len(unique)} insights found (minimum: {min_insights}). "
                f"No report will be generated."
            )
            return

        # 6. Report generation
        self.logger.info("\nSTEP 6: Generating report...")

        statistics = self.analyzer.get_statistics(analyzed)
        statistics['by_source'] = {
            'reddit': len(reddit_posts),
            'youtube': len(youtube_videos)
        }

        # Collect debug messages (e.g., YouTube transcript errors)
        debug_messages = []
        if self.youtube_collector:
            transcript_errors_summary = self.youtube_collector.get_transcript_errors_summary()
            if transcript_errors_summary:
                debug_messages.append(transcript_errors_summary)

        report_result = self.report_generator.generate_report(
            unique,
            statistics=statistics,
            debug_messages=debug_messages if debug_messages else None
        )

        report_path = report_result['path'] if report_result else None

        # Save to cache
        if report_path:
            report_date = datetime.now().strftime('%Y-%m-%d')
            self.cache.save_report_info(
                report_date=report_date,
                report_path=report_path,
                contents_count=len(analyzed),
                relevant_count=len(unique)
            )

        # 7. Discord notification (if enabled)
        discord_config = self.config.get('discord', {})
        if discord_config.get('enabled', False) and report_result:
            self.logger.info("\nSTEP 7: Sending Discord notification...")
            success = False
            try:
                # Check if rich embeds are enabled (with images)
                use_rich_embeds = discord_config.get('rich_embeds', True)

                if use_rich_embeds:
                    # Send rich embeds with images
                    success = self.discord_notifier.send_rich_report(
                        relevant_contents=unique,
                        mention_role=discord_config.get('mention_role', '')
                    )
                else:
                    # Send plain text report (legacy mode)
                    success = self.discord_notifier.send_full_report(
                        report_path=report_result['path'],
                        mention_role=discord_config.get('mention_role', '')
                    )

                # Trigger fallback if send failed
                if not success:
                    self.logger.warning("Discord notification failed, attempting fallback...")
                    send_method = 'send_rich_report' if use_rich_embeds else 'send_full_report'
                    success = self.fallback_manager.retry_with_fallback(
                        notifier=self.discord_notifier,
                        send_method=send_method,
                        report_path=report_result['path'],
                        mention_role=discord_config.get('mention_role', '')
                    )
                    if success:
                        self.logger.info("Discord notification sent successfully via fallback")
                    else:
                        self.logger.error("Discord notification failed even after fallback retries")

            except Exception as e:
                self.logger.error(f"Discord notification raised exception: {e}")
                # Try fallback on exception
                try:
                    self.logger.info("Attempting fallback after exception...")
                    use_rich_embeds = discord_config.get('rich_embeds', True)
                    send_method = 'send_rich_report' if use_rich_embeds else 'send_full_report'
                    success = self.fallback_manager.retry_with_fallback(
                        notifier=self.discord_notifier,
                        send_method=send_method,
                        report_path=report_result['path'],
                        mention_role=discord_config.get('mention_role', '')
                    )
                    if success:
                        self.logger.info("Discord notification sent successfully via fallback after exception")
                except Exception as fallback_error:
                    self.logger.error(f"Fallback also failed: {fallback_error}")

        # 7b. Synology Chat notification (if enabled)
        synology_config = self.config.get('synology', {})
        if synology_config.get('enabled', False) and report_result:
            self.logger.info("\nSTEP 7b: Sending Synology Chat notification...")
            success = False
            try:
                # Synology doesn't support rich embeds, so we send formatted text
                success = self.synology_notifier.send_rich_report(
                    relevant_contents=unique,
                    mention=synology_config.get('mention', '')
                )

                # Trigger fallback if send failed
                if not success:
                    self.logger.warning("Synology Chat notification failed, attempting fallback...")
                    success = self.fallback_manager.retry_with_fallback(
                        notifier=self.synology_notifier,
                        send_method='send_rich_report',
                        report_path=report_result['path'],
                        mention=synology_config.get('mention', '')
                    )
                    if success:
                        self.logger.info("Synology Chat notification sent successfully via fallback")
                    else:
                        self.logger.error("Synology Chat notification failed even after fallback retries")

            except Exception as e:
                self.logger.error(f"Synology Chat notification raised exception: {e}")
                # Try fallback on exception
                try:
                    self.logger.info("Attempting fallback after exception...")
                    success = self.fallback_manager.retry_with_fallback(
                        notifier=self.synology_notifier,
                        send_method='send_rich_report',
                        report_path=report_result['path'],
                        mention=synology_config.get('mention', '')
                    )
                    if success:
                        self.logger.info("Synology Chat notification sent successfully via fallback after exception")
                except Exception as fallback_error:
                    self.logger.error(f"Fallback also failed: {fallback_error}")

        # 8. Discord summary notification (if enabled, separate webhook)
        summary_config = discord_config.get('summary', {})
        summary_text = None  # Initialize for potential reuse by Synology
        discord_summary_success = False

        if summary_config.get('enabled', False) and report_result:
            self.logger.info("\nSTEP 8: Generating and sending Discord summary...")

            # Get retry configuration from fallback settings
            fallback_config = self.config.get('fallback', {})
            max_retries = fallback_config.get('max_retries', 3)
            retry_delay = fallback_config.get('retry_delay', 5.0)

            try:
                # Generate summary using Ollama (will be split if > 2000 chars)
                self.logger.info("Generating daily summary with Ollama...")
                summary_text = self.analyzer.ollama.generate_daily_summary(
                    relevant_contents=unique
                )

                if not summary_text or len(summary_text.strip()) == 0:
                    self.logger.error("Discord summary generation failed: empty summary returned from Ollama")
                else:
                    self.logger.info(f"Summary generated successfully: {len(summary_text)} characters")

                    # Send to summary webhook with retry mechanism
                    mention_role = summary_config.get('mention_role', '')

                    for attempt in range(1, max_retries + 1):
                        self.logger.info(f"Discord summary send attempt {attempt}/{max_retries}...")

                        try:
                            discord_summary_success = self.discord_notifier.send_summary(
                                summary_text=summary_text,
                                mention_role=mention_role
                            )

                            if discord_summary_success:
                                self.logger.info(f"✓ Discord summary sent successfully on attempt {attempt}")
                                break
                            else:
                                self.logger.warning(f"Discord summary send_summary() returned False on attempt {attempt}/{max_retries}")

                                if attempt < max_retries:
                                    delay = retry_delay * (2 ** (attempt - 1))  # Exponential backoff
                                    self.logger.info(f"Retrying in {delay:.1f} seconds...")
                                    time.sleep(delay)

                        except Exception as send_error:
                            self.logger.error(f"Discord summary send raised exception on attempt {attempt}/{max_retries}: {send_error}")

                            if attempt < max_retries:
                                delay = retry_delay * (2 ** (attempt - 1))
                                self.logger.info(f"Retrying in {delay:.1f} seconds...")
                                time.sleep(delay)

                    if not discord_summary_success:
                        self.logger.error(f"✗ Discord summary notification FAILED after {max_retries} attempts")
                        self.logger.error(f"  - Webhook env: {summary_config.get('webhook_env', 'NOT_SET')}")
                        self.logger.error(f"  - Summary length: {len(summary_text)} chars")
                        self.logger.error(f"  - Check Discord webhook URL and network connectivity")

            except Exception as e:
                self.logger.error(f"Discord summary notification failed with exception: {e}")
                self.logger.error(f"  - Exception type: {type(e).__name__}")
                import traceback
                self.logger.error(f"  - Traceback: {traceback.format_exc()}")

        # 8b. Synology Chat summary notification (if enabled, separate webhook)
        synology_summary_config = synology_config.get('summary', {})
        synology_summary_success = False

        if synology_summary_config.get('enabled', False) and report_result:
            self.logger.info("\nSTEP 8b: Sending Synology Chat summary...")

            # Get retry configuration from fallback settings
            fallback_config = self.config.get('fallback', {})
            max_retries = fallback_config.get('max_retries', 3)
            retry_delay = fallback_config.get('retry_delay', 5.0)

            try:
                # Generate summary if not already generated (by Discord step)
                if summary_text is None:
                    self.logger.info("Generating daily summary with Ollama (not generated by Discord step)...")
                    summary_text = self.analyzer.ollama.generate_daily_summary(
                        relevant_contents=unique
                    )

                    if not summary_text or len(summary_text.strip()) == 0:
                        self.logger.error("Synology summary generation failed: empty summary returned from Ollama")
                        summary_text = None
                    else:
                        self.logger.info(f"Summary generated successfully: {len(summary_text)} characters")
                else:
                    self.logger.info(f"Reusing summary from Discord step: {len(summary_text)} characters")

                if summary_text:
                    # Send to Synology summary webhook with retry mechanism
                    mention = synology_summary_config.get('mention', '')

                    for attempt in range(1, max_retries + 1):
                        self.logger.info(f"Synology summary send attempt {attempt}/{max_retries}...")

                        try:
                            synology_summary_success = self.synology_notifier.send_summary(
                                summary_text=summary_text,
                                mention=mention
                            )

                            if synology_summary_success:
                                self.logger.info(f"✓ Synology summary sent successfully on attempt {attempt}")
                                break
                            else:
                                self.logger.warning(f"Synology summary send_summary() returned False on attempt {attempt}/{max_retries}")

                                if attempt < max_retries:
                                    delay = retry_delay * (2 ** (attempt - 1))  # Exponential backoff
                                    self.logger.info(f"Retrying in {delay:.1f} seconds...")
                                    time.sleep(delay)

                        except Exception as send_error:
                            self.logger.error(f"Synology summary send raised exception on attempt {attempt}/{max_retries}: {send_error}")

                            if attempt < max_retries:
                                delay = retry_delay * (2 ** (attempt - 1))
                                self.logger.info(f"Retrying in {delay:.1f} seconds...")
                                time.sleep(delay)

                    if not synology_summary_success:
                        self.logger.error(f"✗ Synology summary notification FAILED after {max_retries} attempts")
                        self.logger.error(f"  - Webhook env: {synology_summary_config.get('webhook_env', 'NOT_SET')}")
                        self.logger.error(f"  - Summary length: {len(summary_text)} chars")
                        self.logger.error(f"  - Check Synology webhook URL and network connectivity")

            except Exception as e:
                self.logger.error(f"Synology Chat summary notification failed with exception: {e}")
                self.logger.error(f"  - Exception type: {type(e).__name__}")
                import traceback
                self.logger.error(f"  - Traceback: {traceback.format_exc()}")

        # 9. Final summary
        self.logger.info("\n" + "=" * 60)
        self.logger.info("INTELLIGENCE CYCLE COMPLETED")
        self.logger.info("=" * 60)
        self.logger.info(f"Package: {pkg_name}")
        self.logger.info(f"Collected: {total_collected} items")
        if nli_filtered_out:
            self.logger.info(f"NLI filtered: {len(nli_filtered_out)} items (skipped LLM)")
        self.logger.info(f"Analyzed (LLM): {len(analyzed)} items")
        self.logger.info(f"Relevant: {len(relevant)} items ({len(relevant)/len(analyzed)*100:.1f}%)")
        self.logger.info(f"Unique: {len(unique)} items")
        self.logger.info(f"Report: {report_path if report_path else 'Not generated'}")

        # Summary notification status
        if summary_config.get('enabled', False):
            status = "✓ SUCCESS" if discord_summary_success else "✗ FAILED"
            self.logger.info(f"Discord Summary: {status}")
        if synology_summary_config.get('enabled', False):
            status = "✓ SUCCESS" if synology_summary_success else "✗ FAILED"
            self.logger.info(f"Synology Summary: {status}")

        self.logger.info("=" * 60 + "\n")

    def _collect_reddit(self):
        """Collect Reddit posts."""
        try:
            posts = self.reddit_collector.collect_posts()

            # Filter by date if configured
            days_back = self.config.get('youtube', {}).get('days_back', 1)
            posts = self.reddit_collector.filter_by_date(posts, days_back)

            self.logger.info(f"Reddit: {len(posts)} posts collected")

            return posts

        except Exception as e:
            self.logger.error(f"Error collecting Reddit: {e}")
            return []

    def _collect_youtube(self):
        """Collect YouTube videos."""
        if self.youtube_collector is None:
            self.logger.info("YouTube: collection disabled")
            return []

        try:
            videos = self.youtube_collector.collect_videos()

            self.logger.info(f"YouTube: {len(videos)} videos with transcripts collected")

            return videos

        except Exception as e:
            self.logger.error(f"Error collecting YouTube: {e}")
            return []

    def _prepare_contents(self, reddit_posts, youtube_videos):
        """Prepare contents for analysis."""
        all_contents = []

        # Reddit
        for post in reddit_posts:
            all_contents.append({
                'id': post['id'],
                'source': 'reddit',
                'title': post['title'],
                'text': self.reddit_collector.get_post_full_text(post),
                'url': post.get('permalink', ''),
                'created_utc': post.get('created_utc'),
                'author': post.get('author'),
                'subreddit': post.get('subreddit'),
                'image_url': post.get('image_url')
            })

        # YouTube
        for video in youtube_videos:
            all_contents.append({
                'id': video['video_id'],
                'source': 'youtube',
                'title': video['title'],
                'text': self.youtube_collector.get_video_full_text(video),
                'url': video.get('url', ''),
                'published_at': video.get('published_at'),
                'channel_title': video.get('channel_title'),
                'video_id': video['video_id']
            })

        return all_contents

    def show_statistics(self):
        """Display cache statistics."""
        stats = self.cache.get_statistics()
        pkg_name = self.package_config.display_name

        print("\n" + "=" * 60)
        print(f"{pkg_name} - STATISTICS")
        print("=" * 60)
        print(f"Total processed: {stats['total_processed']} items")
        print(f"Relevant: {stats['relevant_count']} ({stats['relevance_rate']:.1f}%)")
        print(f"\nBy source:")
        for source, count in stats['by_source'].items():
            print(f"  - {source.title()}: {count}")
        print(f"\nBy category:")
        for category, count in stats['by_category'].items():
            print(f"  - {category}: {count}")
        print(f"\nGenerated reports: {stats['reports_generated']}")
        print("=" * 60 + "\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="SCRIBE - Source Content Retrieval and Intelligence Bot Engine"
    )

    # Package selection
    parser.add_argument(
        '--package', '-p',
        type=str,
        help='Package name to run (e.g., ai_trends)'
    )

    parser.add_argument(
        '--list-packages',
        action='store_true',
        help='List all available packages'
    )

    # Existing arguments
    parser.add_argument(
        '--mode', '-m',
        choices=['once', 'stats'],
        default='once',
        help='Execution mode: once (single run), stats (statistics)'
    )

    parser.add_argument(
        '--language', '--lang', '-l',
        type=str,
        default=None,
        help='Report language (en, fr, es, de, etc.)'
    )

    args = parser.parse_args()

    # List packages
    if args.list_packages:
        pm = PackageManager()
        packages = pm.list_packages()

        if not packages:
            print("No packages found in 'packages/' directory")
            return

        print("\n" + "=" * 60)
        print("AVAILABLE PACKAGES")
        print("=" * 60 + "\n")

        for pkg_name in packages:
            info = pm.get_package_info(pkg_name)
            print(f"  {pkg_name}")
            print(f"    Display name: {info['display_name']}")
            print(f"    Description: {info['description']}")
            print(f"    Language: {info['language']}")
            print(f"    Sources: {info['sources']['reddit_subreddits']} subreddits, "
                  f"{info['sources']['youtube_channels']} channels, "
                  f"{info['sources']['youtube_keywords']} keywords")
            print(f"    Categories: {info['categories']}")
            print(f"    Discord: {'Enabled' if info['discord_enabled'] else 'Disabled'}")
            print()
        return

    # Require package for normal operation
    if not args.package:
        print("Error: No package specified.")
        print("Usage: python main.py --package <name>")
        print("       python main.py --list-packages")
        sys.exit(1)

    # Initialize and run
    try:
        scribe = SCRIBE(package_name=args.package, language=args.language)

        if args.mode == 'stats':
            scribe.show_statistics()
        else:
            scribe.run_veille()

    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Error running SCRIBE: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
