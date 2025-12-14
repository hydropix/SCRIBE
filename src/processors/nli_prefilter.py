"""NLI-based pre-filter for fast content relevance screening.

Uses a lightweight zero-shot classification model to quickly filter out
irrelevant content BEFORE sending to the heavier LLM for detailed analysis.
This significantly reduces LLM calls and processing time.
"""

import logging
from typing import Dict, Any, List, Optional
from functools import lru_cache


class NLIPrefilter:
    """Fast NLI-based pre-filter using zero-shot classification."""

    def __init__(
        self,
        model_name: str = "facebook/bart-large-mnli",
        relevance_labels: List[str] = None,
        threshold: float = 0.5,
        enabled: bool = True,
        max_text_length: int = 512,
        device: str = "cpu"
    ):
        """
        Initialize the NLI pre-filter.

        Args:
            model_name: HuggingFace model for zero-shot classification
            relevance_labels: Labels to classify against (e.g., ["relevant AI news"])
            threshold: Minimum confidence score to keep content (0.0-1.0)
            enabled: Whether pre-filtering is active
            max_text_length: Max characters to analyze (for speed)
            device: Device to run on ("cpu", "cuda", "mps")
        """
        self.logger = logging.getLogger("SCRIBE.NLIPrefilter")
        self.enabled = enabled
        self.threshold = threshold
        self.max_text_length = max_text_length
        self.model_name = model_name
        self.device = device

        # Default labels optimized for tech/AI content
        self.relevance_labels = relevance_labels or [
            "relevant technology or AI news",
            "off-topic or irrelevant content"
        ]

        self._classifier = None

        if self.enabled:
            self._load_model()

    def _load_model(self):
        """Lazy load the classification model."""
        if self._classifier is not None:
            return

        try:
            from transformers import pipeline

            self.logger.info(f"Loading NLI model: {self.model_name}...")

            # Use device_map for better GPU handling if available
            self._classifier = pipeline(
                "zero-shot-classification",
                model=self.model_name,
                device=self.device if self.device != "cpu" else -1
            )

            self.logger.info(f"NLI model loaded successfully on {self.device}")

        except ImportError:
            self.logger.error(
                "transformers library not installed. "
                "Install with: pip install transformers torch"
            )
            self.enabled = False
        except Exception as e:
            self.logger.error(f"Failed to load NLI model: {e}")
            self.enabled = False

    def _prepare_text(self, title: str, text: str) -> str:
        """Prepare text for classification (title + truncated content)."""
        combined = f"{title}. {text}" if text else title
        return combined[:self.max_text_length]

    def classify_single(
        self,
        title: str,
        text: str = "",
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Classify a single content item.

        Args:
            title: Content title
            text: Content body
            metadata: Optional metadata (not used in classification but passed through)

        Returns:
            Dict with 'is_relevant', 'nli_score', 'nli_label'
        """
        if not self.enabled or self._classifier is None:
            return {
                'is_relevant': True,  # Pass through if disabled
                'nli_score': 1.0,
                'nli_label': 'skipped'
            }

        prepared_text = self._prepare_text(title, text)

        try:
            result = self._classifier(
                prepared_text,
                self.relevance_labels,
                multi_label=False
            )

            # First label is the "relevant" one
            relevant_label = self.relevance_labels[0]

            # Find score for relevant label
            label_idx = result['labels'].index(relevant_label)
            relevance_score = result['scores'][label_idx]

            is_relevant = relevance_score >= self.threshold

            return {
                'is_relevant': is_relevant,
                'nli_score': round(relevance_score, 3),
                'nli_label': result['labels'][0]  # Top predicted label
            }

        except Exception as e:
            self.logger.warning(f"NLI classification failed for '{title[:50]}...': {e}")
            return {
                'is_relevant': True,  # Pass through on error
                'nli_score': 0.0,
                'nli_label': 'error'
            }

    def filter_batch(
        self,
        contents: List[Dict[str, Any]],
        content_key: str = 'text',
        title_key: str = 'title'
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Filter a batch of contents using NLI.

        Args:
            contents: List of content dicts
            content_key: Key for content text
            title_key: Key for title

        Returns:
            Tuple of (relevant_contents, filtered_out_contents)
        """
        if not self.enabled:
            self.logger.info("NLI pre-filter disabled, passing all contents through")
            return contents, []

        self.logger.info(f"NLI pre-filtering {len(contents)} contents (threshold: {self.threshold})...")

        relevant = []
        filtered_out = []

        for i, content in enumerate(contents, 1):
            title = content.get(title_key, '')
            text = content.get(content_key, '')

            result = self.classify_single(title, text)

            # Enrich content with NLI metadata
            content_with_nli = content.copy()
            content_with_nli['nli_score'] = result['nli_score']
            content_with_nli['nli_label'] = result['nli_label']

            if result['is_relevant']:
                relevant.append(content_with_nli)
            else:
                filtered_out.append(content_with_nli)

            if i % 20 == 0:
                self.logger.info(f"NLI Progress: {i}/{len(contents)}")

        # Statistics
        pct_kept = (len(relevant) / len(contents) * 100) if contents else 0
        self.logger.info(
            f"NLI pre-filter complete: {len(relevant)}/{len(contents)} passed "
            f"({pct_kept:.1f}%), {len(filtered_out)} filtered out"
        )

        return relevant, filtered_out

    def get_statistics(self, filtered_out: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get statistics about filtered content."""
        if not filtered_out:
            return {'filtered_count': 0}

        scores = [c.get('nli_score', 0) for c in filtered_out]

        return {
            'filtered_count': len(filtered_out),
            'avg_score': round(sum(scores) / len(scores), 3) if scores else 0,
            'min_score': round(min(scores), 3) if scores else 0,
            'max_score': round(max(scores), 3) if scores else 0,
        }


if __name__ == "__main__":
    # Quick test
    logging.basicConfig(level=logging.INFO)

    prefilter = NLIPrefilter(
        threshold=0.5,
        enabled=True
    )

    test_contents = [
        {
            'title': 'GPT-5 Released with Major Improvements in Reasoning',
            'text': 'OpenAI announced GPT-5 today with significant improvements in reasoning and coding capabilities.',
            'source': 'reddit'
        },
        {
            'title': 'My cat is so cute today',
            'text': 'Just wanted to share a picture of my adorable cat sleeping.',
            'source': 'reddit'
        },
        {
            'title': 'New Transformer Architecture Achieves SOTA on Benchmarks',
            'text': 'Researchers published a new attention mechanism that achieves state-of-the-art results.',
            'source': 'reddit'
        },
        {
            'title': 'Best pizza recipe ever',
            'text': 'I made the most delicious pizza last night using this simple recipe.',
            'source': 'reddit'
        },
        {
            'title': 'Claude 4 vs GPT-4: Which is better for coding?',
            'text': 'A detailed comparison of the latest AI assistants for software development.',
            'source': 'reddit'
        }
    ]

    relevant, filtered = prefilter.filter_batch(test_contents)

    print("\n" + "=" * 60)
    print("NLI PRE-FILTER TEST RESULTS")
    print("=" * 60)

    print(f"\nRelevant ({len(relevant)}):")
    for c in relevant:
        print(f"  [{c['nli_score']:.2f}] {c['title'][:60]}")

    print(f"\nFiltered out ({len(filtered)}):")
    for c in filtered:
        print(f"  [{c['nli_score']:.2f}] {c['title'][:60]}")

    stats = prefilter.get_statistics(filtered)
    print(f"\nStatistics: {stats}")
