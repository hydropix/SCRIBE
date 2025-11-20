#!/usr/bin/env python3
"""
SCRIBE - Source Content Retrieval and Intelligence Bot Engine

Multi-package intelligence gathering system.
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

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
from src.storage.cache_manager import CacheManager
from src.storage.report_generator import ReportGenerator
from src.notifiers.discord_notifier import DiscordNotifier
from src.notifiers.synology_notifier import SynologyNotifier


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
        self.youtube_collector = YouTubeCollector(config=pkg.settings)

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
            language=language_full
        )

        # Initialize notifiers with package config
        discord_config = pkg.settings.get('discord', {})
        self.discord_notifier = DiscordNotifier(config=discord_config)

        synology_config = pkg.settings.get('synology', {})
        self.synology_notifier = SynologyNotifier(config=synology_config)

        self.logger.info("All components initialized successfully")

    def run_veille(self):
        """Execute a complete intelligence gathering cycle."""
        pkg_name = self.package_config.name

        self.logger.info("\n" + "=" * 60)
        self.logger.info(f"Starting intelligence cycle at {datetime.now()}")
        self.logger.info("=" * 60 + "\n")

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

        report_result = self.report_generator.generate_report(
            unique,
            statistics=statistics
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
            try:
                # Check if rich embeds are enabled (with images)
                use_rich_embeds = discord_config.get('rich_embeds', True)

                if use_rich_embeds:
                    # Send rich embeds with images
                    self.discord_notifier.send_rich_report(
                        relevant_contents=unique,
                        mention_role=discord_config.get('mention_role', '')
                    )
                else:
                    # Send plain text report (legacy mode)
                    self.discord_notifier.send_full_report(
                        report_path=report_result['path'],
                        mention_role=discord_config.get('mention_role', '')
                    )
            except Exception as e:
                self.logger.error(f"Discord notification failed (non-blocking): {e}")

        # 7b. Synology Chat notification (if enabled)
        synology_config = self.config.get('synology', {})
        if synology_config.get('enabled', False) and report_result:
            self.logger.info("\nSTEP 7b: Sending Synology Chat notification...")
            try:
                # Synology doesn't support rich embeds, so we send formatted text
                self.synology_notifier.send_rich_report(
                    relevant_contents=unique,
                    mention=synology_config.get('mention', '')
                )
            except Exception as e:
                self.logger.error(f"Synology Chat notification failed (non-blocking): {e}")

        # 8. Discord summary notification (if enabled, separate webhook)
        summary_config = discord_config.get('summary', {})
        if summary_config.get('enabled', False) and report_result:
            self.logger.info("\nSTEP 8: Generating and sending Discord summary...")
            try:
                # Generate summary using Ollama (will be split if > 2000 chars)
                summary_text = self.analyzer.ollama.generate_daily_summary(
                    relevant_contents=unique
                )

                # Send to summary webhook (auto-splits if needed)
                self.discord_notifier.send_summary(
                    summary_text=summary_text,
                    mention_role=summary_config.get('mention_role', '')
                )

                self.logger.info(f"Summary generated: {len(summary_text)} characters")

            except Exception as e:
                self.logger.error(f"Discord summary notification failed (non-blocking): {e}")

        # 8b. Synology Chat summary notification (if enabled, separate webhook)
        synology_summary_config = synology_config.get('summary', {})
        if synology_summary_config.get('enabled', False) and report_result:
            self.logger.info("\nSTEP 8b: Sending Synology Chat summary...")
            try:
                # Generate summary if not already generated
                if not summary_config.get('enabled', False):
                    summary_text = self.analyzer.ollama.generate_daily_summary(
                        relevant_contents=unique
                    )
                # Reuse the summary generated for Discord

                # Send to Synology summary webhook (auto-splits if needed)
                self.synology_notifier.send_summary(
                    summary_text=summary_text,
                    mention=synology_summary_config.get('mention', '')
                )

                self.logger.info(f"Synology summary sent: {len(summary_text)} characters")

            except Exception as e:
                self.logger.error(f"Synology Chat summary notification failed (non-blocking): {e}")

        # 9. Final summary
        self.logger.info("\n" + "=" * 60)
        self.logger.info("INTELLIGENCE CYCLE COMPLETED")
        self.logger.info("=" * 60)
        self.logger.info(f"Package: {pkg_name}")
        self.logger.info(f"Collected: {total_collected} items")
        self.logger.info(f"Analyzed: {len(analyzed)} items")
        self.logger.info(f"Relevant: {len(relevant)} items ({len(relevant)/len(analyzed)*100:.1f}%)")
        self.logger.info(f"Unique: {len(unique)} items")
        self.logger.info(f"Report: {report_path if report_path else 'Not generated'}")
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
