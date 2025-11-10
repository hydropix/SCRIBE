"""SQLite cache manager to avoid reprocessing contents"""

import sqlite3
import logging
import json
from typing import Optional, List, Dict, Any
from datetime import datetime
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))


class CacheManager:
    """Manages the cache of already processed contents"""

    @staticmethod
    def _serialize_metadata(metadata: Dict[str, Any]) -> str:
        """Converts metadata to JSON handling datetime objects"""
        def convert_datetime(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Type {type(obj)} not serializable")

        return json.dumps(metadata, default=convert_datetime)

    def __init__(self, db_path: str = "data/cache.db"):
        """
        Initializes the cache manager

        Args:
            db_path: Path to the SQLite database
        """
        self.logger = logging.getLogger("SCRIBE.CacheManager")
        self.db_path = Path(db_path)

        # Create folder if necessary
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Create tables
        self._init_database()

        self.logger.info(f"Cache manager initialized: {self.db_path}")

    def _init_database(self):
        """Creates the tables if they don't exist"""

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Table for processed contents
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS processed_contents (
                    id TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    title TEXT,
                    url TEXT,
                    processed_at TEXT NOT NULL,
                    was_relevant BOOLEAN,
                    category TEXT,
                    metadata TEXT
                )
            """)

            # Table for generated reports
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS generated_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    report_date TEXT NOT NULL,
                    report_path TEXT NOT NULL,
                    contents_count INTEGER,
                    relevant_count INTEGER,
                    generated_at TEXT NOT NULL
                )
            """)

            # Index for fast search
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_source_id
                ON processed_contents(source, id)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_processed_at
                ON processed_contents(processed_at)
            """)

            conn.commit()

        self.logger.debug("Database initialized")

    def is_processed(self, content_id: str, source: str) -> bool:
        """
        Checks if a content has already been processed

        Args:
            content_id: Content ID
            source: Source (reddit, youtube)

        Returns:
            True if already processed
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                "SELECT 1 FROM processed_contents WHERE id = ? AND source = ?",
                (content_id, source)
            )

            return cursor.fetchone() is not None

    def mark_processed(
        self,
        content_id: str,
        source: str,
        title: str = "",
        url: str = "",
        was_relevant: bool = False,
        category: str = "",
        metadata: Dict[str, Any] = None
    ):
        """
        Marks a content as processed

        Args:
            content_id: Content ID
            source: Source (reddit, youtube)
            title: Content title
            url: Content URL
            was_relevant: Whether the content was relevant
            category: Assigned category
            metadata: Additional metadata
        """
        metadata = metadata or {}

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT OR REPLACE INTO processed_contents
                (id, source, title, url, processed_at, was_relevant, category, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                content_id,
                source,
                title,
                url,
                datetime.now().isoformat(),
                was_relevant,
                category,
                self._serialize_metadata(metadata)
            ))

            conn.commit()

    def batch_mark_processed(self, contents: List[Dict[str, Any]]):
        """
        Marks multiple contents as processed

        Args:
            contents: List of contents with their metadata
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            for content in contents:
                metadata = content.get('metadata', {})
                content_id = metadata.get('id', '')
                source = metadata.get('source', 'unknown')

                if not content_id:
                    continue

                cursor.execute("""
                    INSERT OR REPLACE INTO processed_contents
                    (id, source, title, url, processed_at, was_relevant, category, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    content_id,
                    source,
                    content.get('title', ''),
                    metadata.get('url', '') or metadata.get('permalink', ''),
                    datetime.now().isoformat(),
                    content.get('is_relevant', False),
                    content.get('category', ''),
                    self._serialize_metadata(metadata)
                ))

            conn.commit()

        self.logger.info(f"Marked {len(contents)} contents as processed")

    def filter_unprocessed(
        self,
        contents: List[Dict[str, Any]],
        id_key: str = 'id',
        source_key: str = 'source'
    ) -> List[Dict[str, Any]]:
        """
        Filters a list to keep only unprocessed contents

        Args:
            contents: List of contents
            id_key: Key for the ID
            source_key: Key for the source

        Returns:
            List of unprocessed contents
        """
        unprocessed = []

        for content in contents:
            content_id = content.get(id_key)
            source = content.get(source_key, 'unknown')

            if not content_id or not self.is_processed(content_id, source):
                unprocessed.append(content)

        filtered_count = len(contents) - len(unprocessed)
        if filtered_count > 0:
            self.logger.info(
                f"Filtered {filtered_count}/{len(contents)} already processed contents"
            )

        return unprocessed

    def save_report_info(
        self,
        report_date: str,
        report_path: str,
        contents_count: int,
        relevant_count: int
    ):
        """
        Saves information about a generated report

        Args:
            report_date: Report date
            report_path: Report file path
            contents_count: Total number of contents
            relevant_count: Number of relevant contents
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO generated_reports
                (report_date, report_path, contents_count, relevant_count, generated_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                report_date,
                report_path,
                contents_count,
                relevant_count,
                datetime.now().isoformat()
            ))

            conn.commit()

        self.logger.info(f"Saved report info: {report_path}")

    def get_statistics(self) -> Dict[str, Any]:
        """
        Retrieves cache statistics

        Returns:
            Dictionary of statistics
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Total processed contents
            cursor.execute("SELECT COUNT(*) FROM processed_contents")
            total_processed = cursor.fetchone()[0]

            # Relevant contents
            cursor.execute("SELECT COUNT(*) FROM processed_contents WHERE was_relevant = 1")
            relevant_count = cursor.fetchone()[0]

            # By source
            cursor.execute("""
                SELECT source, COUNT(*)
                FROM processed_contents
                GROUP BY source
            """)
            by_source = dict(cursor.fetchall())

            # By category
            cursor.execute("""
                SELECT category, COUNT(*)
                FROM processed_contents
                WHERE was_relevant = 1
                GROUP BY category
            """)
            by_category = dict(cursor.fetchall())

            # Generated reports
            cursor.execute("SELECT COUNT(*) FROM generated_reports")
            reports_count = cursor.fetchone()[0]

        return {
            'total_processed': total_processed,
            'relevant_count': relevant_count,
            'relevance_rate': (relevant_count / total_processed * 100) if total_processed > 0 else 0,
            'by_source': by_source,
            'by_category': by_category,
            'reports_generated': reports_count
        }

    def cleanup_old_entries(self, days_to_keep: int = 30):
        """
        Cleans up old cache entries

        Args:
            days_to_keep: Number of days to keep
        """
        cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).isoformat()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                "DELETE FROM processed_contents WHERE processed_at < ?",
                (cutoff_date,)
            )

            deleted = cursor.rowcount
            conn.commit()

        self.logger.info(f"Cleaned up {deleted} old cache entries")


if __name__ == "__main__":
    # Quick test
    from datetime import timedelta
    import sys
    sys.path.append(str(Path(__file__).parent.parent.parent))

    from src.utils import setup_logging

    setup_logging()

    cache = CacheManager("data/test_cache.db")

    # Add test
    cache.mark_processed(
        content_id="test123",
        source="reddit",
        title="Test Post",
        url="http://example.com",
        was_relevant=True,
        category="Test"
    )

    # Verification test
    print(f"Is processed: {cache.is_processed('test123', 'reddit')}")
    print(f"Is processed (unknown): {cache.is_processed('unknown', 'reddit')}")

    # Statistics
    stats = cache.get_statistics()
    print("\nStatistics:")
    print(json.dumps(stats, indent=2))
