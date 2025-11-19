"""
SCRIBE - Source Content Retrieval and Intelligence Bot Engine

Système de veille automatisé sur l'Intelligence Artificielle.
Point d'entrée principal du système.
"""

import argparse
import logging
from datetime import datetime
from pathlib import Path

from src.utils import (
    setup_logging,
    load_env_variables,
    ensure_directories,
    load_config,
    clear_raw_logs,
    save_raw_data_log
)
from src.collectors.reddit_collector import RedditCollector
from src.collectors.youtube_collector import YouTubeCollector
from src.processors.content_analyzer import ContentAnalyzer
from src.processors.deduplicator import ContentDeduplicator
from src.storage.cache_manager import CacheManager
from src.storage.report_generator import ReportGenerator
from src.notifiers.discord_notifier import DiscordNotifier


class SCRIBE:
    """Main orchestrator for the SCRIBE intelligence system"""

    def __init__(self, language: str = None):
        """Initialize the intelligence system

        Args:
            language: Language code for report generation (en, fr, es, etc.)
        """

        # Configure logging
        self.logger = setup_logging()
        self.logger.info("=" * 60)
        self.logger.info("SCRIBE - Source Content Retrieval and Intelligence Bot Engine")
        self.logger.info("=" * 60)

        # Load environment variables
        try:
            load_env_variables()
        except FileNotFoundError as e:
            self.logger.error(str(e))
            raise

        # Create necessary directories
        ensure_directories()

        # Load config for options
        self.config = load_config("config/settings.yaml")

        # Get language from parameter or config
        if language is None:
            language = self.config.get('reports', {}).get('language', 'en')

        self.language = language

        # Map language codes to full names for components
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
        language_full = language_map.get(language, 'English')

        # Initialize components
        self.logger.info(f"Initializing components (language: {language_full})...")

        self.reddit_collector = RedditCollector()
        self.youtube_collector = YouTubeCollector()
        self.analyzer = ContentAnalyzer(language=language_full)
        self.deduplicator = ContentDeduplicator()
        self.cache = CacheManager()
        self.report_generator = ReportGenerator(language=language_full)
        self.discord_notifier = DiscordNotifier()

        self.logger.info("All components initialized successfully")

    def run_veille(self):
        """Execute a complete intelligence gathering cycle"""

        self.logger.info("\n" + "=" * 60)
        self.logger.info(f"Starting intelligence cycle at {datetime.now()}")
        self.logger.info("=" * 60 + "\n")

        # 0. Cache cleanup (remove entries older than 3 months)
        self.logger.info("STEP 0: Cleaning up old cache entries...")
        self.cache.cleanup_old_entries(days_to_keep=90)

        # 0.5 Clear previous raw data logs
        self.logger.info("Clearing previous raw data logs...")
        clear_raw_logs()

        # 1. Data collection
        self.logger.info("\nSTEP 1: Collecting data from sources...")

        reddit_posts = self._collect_reddit()
        youtube_videos = self._collect_youtube()

        # Save raw data to markdown logs
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        if reddit_posts:
            reddit_log_path = save_raw_data_log(reddit_posts, 'reddit', timestamp)
            self.logger.info(f"Raw Reddit data saved to: {reddit_log_path}")
        if youtube_videos:
            youtube_log_path = save_raw_data_log(youtube_videos, 'youtube', timestamp)
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

        # 9. Final summary
        self.logger.info("\n" + "=" * 60)
        self.logger.info("INTELLIGENCE CYCLE COMPLETED")
        self.logger.info("=" * 60)
        self.logger.info(f"Collected: {total_collected} items")
        self.logger.info(f"Analyzed: {len(analyzed)} items")
        self.logger.info(f"Relevant: {len(relevant)} items ({len(relevant)/len(analyzed)*100:.1f}%)")
        self.logger.info(f"Unique: {len(unique)} items")
        self.logger.info(f"Report: {report_path if report_path else 'Not generated'}")
        self.logger.info("=" * 60 + "\n")

    def _collect_reddit(self):
        """Collect Reddit posts"""

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
        """Collect YouTube videos"""

        try:
            videos = self.youtube_collector.collect_videos()

            self.logger.info(f"YouTube: {len(videos)} videos with transcripts collected")

            return videos

        except Exception as e:
            self.logger.error(f"Error collecting YouTube: {e}")
            return []

    def _prepare_contents(self, reddit_posts, youtube_videos):
        """Prepare contents for analysis"""

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
                'image_url': post.get('image_url')  # Include image URL if available
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
                'video_id': video['video_id']  # Include video_id for thumbnail
            })

        return all_contents

    def show_statistics(self):
        """Display cache statistics"""

        stats = self.cache.get_statistics()

        print("\n" + "=" * 60)
        print("SCRIBE - STATISTICS")
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
    """Main entry point"""

    parser = argparse.ArgumentParser(
        description="SCRIBE - Source Content Retrieval and Intelligence Bot Engine"
    )

    parser.add_argument(
        '--mode',
        choices=['once', 'stats'],
        default='once',
        help='Execution mode: once (single run), stats (statistics)'
    )

    parser.add_argument(
        '--language', '--lang',
        type=str,
        default=None,
        help='Report language (en, fr, es, de, etc.). Default: from config (en)'
    )

    args = parser.parse_args()

    # Initialize the system with language parameter
    scribe = SCRIBE(language=args.language)

    if args.mode == 'stats':
        # Display statistics
        scribe.show_statistics()

    elif args.mode == 'once':
        # Single execution
        scribe.run_veille()


if __name__ == "__main__":
    main()
