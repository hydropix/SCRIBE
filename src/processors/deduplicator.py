"""Content deduplicator using fast similarity detection"""

import logging
from typing import List, Dict, Any, Set
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.processors.ollama_client import OllamaClient
from src.processors.fast_similarity import FastSimilarityDetector


class ContentDeduplicator:
    """Detects and eliminates redundant contents"""

    def __init__(
        self,
        ollama_config: dict = None,
        use_fast_detection: bool = True,
        tfidf_threshold: float = 0.67,
        simhash_threshold: float = 0.85
    ):
        """
        Initializes the deduplicator

        Args:
            ollama_config: Ollama configuration dict (model, temperature, etc.)
            use_fast_detection: Use fast similarity detection instead of LLM
            tfidf_threshold: Threshold for TF-IDF semantic similarity (0.67 recommended)
            simhash_threshold: Threshold for SimHash near-duplicate detection (0.85 recommended)
        """
        self.logger = logging.getLogger("SCRIBE.Deduplicator")
        self.use_fast_detection = use_fast_detection
        self.tfidf_threshold = tfidf_threshold
        self.simhash_threshold = simhash_threshold

        # Initialize fast similarity detector (primary method)
        if use_fast_detection:
            self.fast_detector = FastSimilarityDetector(
                tfidf_threshold=tfidf_threshold,
                simhash_threshold=simhash_threshold
            )
            self.logger.info(f"Fast similarity detector initialized (tfidf={tfidf_threshold}, simhash={simhash_threshold})")

        # Keep Ollama as fallback (optional)
        if ollama_config:
            self.ollama = OllamaClient(config=ollama_config)
        else:
            self.ollama = None

        self.logger.info("Deduplicator initialized")

    def deduplicate(
        self,
        contents: List[Dict[str, Any]],
        title_key: str = 'title',
        text_key: str = 'insights'
    ) -> List[Dict[str, Any]]:
        """
        Eliminates redundant contents from a list

        Args:
            contents: List of contents to deduplicate
            title_key: Key for title
            text_key: Key for text to compare

        Returns:
            List of unique contents
        """
        if not contents:
            return []

        self.logger.info(f"Deduplicating {len(contents)} contents...")

        unique_contents = []
        seen_ids: Set[str] = set()  # For deduplication by exact ID

        for i, content in enumerate(contents):
            # Retrieve ID if available (Reddit/YouTube)
            content_id = content.get('metadata', {}).get('id')

            # Deduplication by exact ID
            if content_id and content_id in seen_ids:
                self.logger.debug(f"Skipping duplicate ID: {content_id}")
                continue

            # Check semantic similarity with already kept contents
            is_duplicate = False

            if unique_contents:
                is_duplicate = self._check_semantic_duplicates(
                    content,
                    unique_contents,
                    title_key,
                    text_key
                )

            if not is_duplicate:
                unique_contents.append(content)
                if content_id:
                    seen_ids.add(content_id)

                self.logger.debug(f"✓ Unique: {content.get(title_key, 'Unknown')[:50]}")
            else:
                self.logger.debug(f"✗ Duplicate: {content.get(title_key, 'Unknown')[:50]}")

            # Progress log
            if (i + 1) % 20 == 0:
                self.logger.info(
                    f"Progress: {i + 1}/{len(contents)} - "
                    f"Unique: {len(unique_contents)}"
                )

        removed_count = len(contents) - len(unique_contents)
        self.logger.info(
            f"Deduplication complete: {len(unique_contents)} unique contents "
            f"({removed_count} duplicates removed, {removed_count/len(contents)*100:.1f}%)"
        )

        return unique_contents

    def _check_semantic_duplicates(
        self,
        new_content: Dict[str, Any],
        existing_contents: List[Dict[str, Any]],
        title_key: str,
        text_key: str
    ) -> bool:
        """
        Checks if content is semantically similar to existing contents

        Args:
            new_content: The new content to check
            existing_contents: Already validated contents
            title_key: Key for title
            text_key: Key for text

        Returns:
            True if duplicate, False otherwise
        """
        new_text = self._get_comparison_text(new_content, title_key, text_key)
        new_title = new_content.get(title_key, '')

        # Compare with existing contents (starting from end, most recent)
        # Limit to last 50 contents for performance
        check_limit = min(50, len(existing_contents))

        # Use fast detection if enabled
        if self.use_fast_detection:
            existing_texts = []
            existing_titles = []

            for existing in existing_contents[-check_limit:]:
                existing_texts.append(self._get_comparison_text(existing, title_key, text_key))
                existing_titles.append(existing.get(title_key, ''))

            is_dup, similarity, idx = self.fast_detector.is_duplicate(
                new_text,
                existing_texts,
                new_title,
                existing_titles,
                self.tfidf_threshold
            )

            if is_dup:
                self.logger.debug(
                    f"Duplicate detected (fast): similarity={similarity:.3f} "
                    f"with '{existing_titles[idx][:50]}...'"
                )
                return True

            return False

        # Fallback to LLM-based detection (slower)
        if not self.ollama:
            return False

        for existing in existing_contents[-check_limit:]:
            existing_text = self._get_comparison_text(existing, title_key, text_key)

            # Quick check for exact title similarity
            if new_content.get(title_key, '').lower() == existing.get(title_key, '').lower():
                self.logger.debug("Duplicate detected: exact title match")
                return True

            # Semantic check with Ollama
            try:
                level, explanation = self.ollama.check_similarity(new_text, existing_text)

                if level == 'IDENTIQUE':
                    self.logger.debug(f"Duplicate detected: {explanation}")
                    return True

            except Exception as e:
                self.logger.warning(f"Error checking similarity: {e}")
                # In case of error, don't consider as duplicate (conservative)
                continue

        return False

    def _get_comparison_text(
        self,
        content: Dict[str, Any],
        title_key: str,
        text_key: str
    ) -> str:
        """
        Builds the text to compare for deduplication

        Args:
            content: The content
            title_key: Title key
            text_key: Text key

        Returns:
            Combined text for comparison
        """
        title = content.get(title_key, '')
        text = content.get(text_key, '')

        # Limit length for efficiency
        if text:
            text = text[:1000]

        return f"{title}\n\n{text}"

    def deduplicate_by_url(
        self,
        contents: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Simple deduplication by URL (for Reddit/YouTube)

        Args:
            contents: List of contents with metadata

        Returns:
            Contents deduplicated by URL
        """
        seen_urls: Set[str] = set()
        unique = []

        for content in contents:
            url = content.get('metadata', {}).get('url') or content.get('metadata', {}).get('permalink')

            if url and url in seen_urls:
                continue

            unique.append(content)
            if url:
                seen_urls.add(url)

        removed = len(contents) - len(unique)
        if removed > 0:
            self.logger.info(f"Removed {removed} duplicates by URL")

        return unique

    def group_similar(
        self,
        contents: List[Dict[str, Any]],
        title_key: str = 'title',
        text_key: str = 'insights'
    ) -> List[List[Dict[str, Any]]]:
        """
        Groups similar contents together (without removing them)

        Args:
            contents: List of contents
            title_key: Title key
            text_key: Text key

        Returns:
            List of groups of similar contents
        """
        self.logger.info(f"Grouping {len(contents)} similar contents...")

        if not self.ollama:
            self.logger.warning("Ollama not configured, returning contents ungrouped")
            return [[c] for c in contents]

        groups = []
        ungrouped = contents.copy()

        while ungrouped:
            # Take first ungrouped content
            current = ungrouped.pop(0)
            current_group = [current]

            # Search for similar contents
            remaining = []

            for candidate in ungrouped:
                current_text = self._get_comparison_text(current, title_key, text_key)
                candidate_text = self._get_comparison_text(candidate, title_key, text_key)

                try:
                    level, _ = self.ollama.check_similarity(current_text, candidate_text)

                    if level in ['IDENTIQUE', 'SIMILAIRE']:
                        current_group.append(candidate)
                    else:
                        remaining.append(candidate)

                except Exception as e:
                    self.logger.warning(f"Error grouping: {e}")
                    remaining.append(candidate)

            groups.append(current_group)
            ungrouped = remaining

        self.logger.info(f"Created {len(groups)} groups")

        # Sort by group size (descending)
        groups.sort(key=len, reverse=True)

        return groups


if __name__ == "__main__":
    # Quick test
    import sys
    sys.path.append(str(Path(__file__).parent.parent.parent))

    from src.utils import setup_logging

    setup_logging()

    dedup = ContentDeduplicator()

    # Test with similar contents
    test_contents = [
        {
            'title': 'GPT-5 Released',
            'insights': 'OpenAI released GPT-5 with improved reasoning capabilities.',
            'metadata': {'id': '1', 'url': 'http://example.com/1'}
        },
        {
            'title': 'OpenAI Announces GPT-5',
            'insights': 'GPT-5 has been released by OpenAI with better reasoning.',
            'metadata': {'id': '2', 'url': 'http://example.com/2'}
        },
        {
            'title': 'New Vision Transformer Published',
            'insights': 'Researchers published a new ViT architecture.',
            'metadata': {'id': '3', 'url': 'http://example.com/3'}
        }
    ]

    unique = dedup.deduplicate(test_contents)

    print(f"\nOriginal: {len(test_contents)} contents")
    print(f"After deduplication: {len(unique)} contents")

    print("\nUnique contents:")
    for c in unique:
        print(f"  - {c['title']}")
