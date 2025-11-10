"""Content analyzer using Ollama for filtering and categorizing"""

import logging
from typing import Dict, Any, List
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.processors.ollama_client import OllamaClient
from src.utils import load_config


class ContentAnalyzer:
    """Analyzes collected contents with Ollama"""

    def __init__(
        self,
        settings_path: str = "config/settings.yaml",
        ollama_config_path: str = "config/ollama_config.yaml"
    ):
        """
        Initializes the content analyzer

        Args:
            settings_path: Path to settings.yaml
            ollama_config_path: Path to ollama_config.yaml
        """
        self.logger = logging.getLogger("SCRIBE.ContentAnalyzer")
        self.config = load_config(settings_path)
        self.analysis_config = self.config.get('analysis', {})

        # Initialize Ollama client
        self.ollama = OllamaClient(ollama_config_path)

        self.relevance_threshold = self.analysis_config.get('relevance_threshold', 7)
        self.categories = self.analysis_config.get('categories', [])

        self.logger.info("Content analyzer initialized")

    def analyze_content(
        self,
        content: str,
        title: str = "",
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Analyzes content to determine relevance and extract insights

        Args:
            content: The text content to analyze
            title: The content title
            metadata: Additional metadata

        Returns:
            Dictionary with analysis results
        """
        metadata = metadata or {}

        self.logger.debug(f"Analyzing: {title[:50]}...")

        # 1. Relevance analysis
        relevance = self.ollama.analyze_relevance(content, title)

        # Check relevance threshold
        is_relevant = (
            relevance.get('pertinent', False) and
            relevance.get('score', 0) >= self.relevance_threshold
        )

        result = {
            'title': title,
            'is_relevant': is_relevant,
            'relevance_score': relevance.get('score', 0),
            'relevance_reason': relevance.get('raison', ''),
            'category': relevance.get('categorie', 'Unknown'),
            'insights': None,
            'metadata': metadata
        }

        # 2. Extract insights if relevant
        if is_relevant:
            try:
                insights = self.ollama.extract_insights(content, title)
                result['insights'] = insights
                self.logger.info(f"✓ Relevant ({relevance['score']}/10): {title[:60]}")
            except Exception as e:
                self.logger.error(f"Error extracting insights: {e}")
                result['insights'] = "Erreur lors de l'extraction des insights"
        else:
            self.logger.debug(f"✗ Not relevant ({relevance['score']}/10): {title[:60]}")

        return result

    def batch_analyze(
        self,
        contents: List[Dict[str, Any]],
        content_key: str = 'text',
        title_key: str = 'title'
    ) -> List[Dict[str, Any]]:
        """
        Analyzes a batch of contents

        Args:
            contents: List of contents to analyze
            content_key: Key for content text
            title_key: Key for title

        Returns:
            List of analysis results
        """
        self.logger.info(f"Batch analyzing {len(contents)} contents...")

        results = []

        for i, content_item in enumerate(contents, 1):
            try:
                text = content_item.get(content_key, '')
                title = content_item.get(title_key, '')

                # Copy metadata
                metadata = {k: v for k, v in content_item.items() if k not in [content_key, title_key]}

                result = self.analyze_content(text, title, metadata)
                results.append(result)

                if i % 10 == 0:
                    self.logger.info(f"Progress: {i}/{len(contents)}")

            except Exception as e:
                self.logger.error(f"Error analyzing content {i}: {e}")
                results.append({
                    'title': content_item.get(title_key, 'Unknown'),
                    'is_relevant': False,
                    'relevance_score': 0,
                    'relevance_reason': f'Error: {str(e)}',
                    'category': 'Error',
                    'insights': None,
                    'metadata': content_item
                })

        # Statistics
        relevant_count = sum(1 for r in results if r['is_relevant'])
        self.logger.info(
            f"Analysis complete: {relevant_count}/{len(results)} contents marked as relevant "
            f"({relevant_count/len(results)*100:.1f}%)"
        )

        return results

    def filter_relevant(self, analysis_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filters to keep only relevant contents

        Args:
            analysis_results: Analysis results

        Returns:
            Only relevant contents
        """
        relevant = [r for r in analysis_results if r['is_relevant']]

        self.logger.info(f"Filtered: {len(relevant)}/{len(analysis_results)} relevant contents")

        return relevant

    def group_by_category(
        self,
        analysis_results: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Groups contents by category

        Args:
            analysis_results: Analysis results

        Returns:
            Dictionary {category: [contents]}
        """
        grouped = {}

        for result in analysis_results:
            category = result.get('category', 'Unknown')

            if category not in grouped:
                grouped[category] = []

            grouped[category].append(result)

        # Sort by number of contents
        sorted_grouped = dict(
            sorted(grouped.items(), key=lambda x: len(x[1]), reverse=True)
        )

        self.logger.info(f"Grouped into {len(sorted_grouped)} categories")

        return sorted_grouped

    def get_statistics(
        self,
        analysis_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculates statistics on analysis results

        Args:
            analysis_results: Analysis results

        Returns:
            Statistics dictionary
        """
        total = len(analysis_results)
        relevant = sum(1 for r in analysis_results if r['is_relevant'])

        categories = {}
        for result in analysis_results:
            if result['is_relevant']:
                cat = result.get('category', 'Unknown')
                categories[cat] = categories.get(cat, 0) + 1

        avg_score = (
            sum(r['relevance_score'] for r in analysis_results) / total
            if total > 0 else 0
        )

        stats = {
            'total_analyzed': total,
            'relevant_count': relevant,
            'relevant_percentage': (relevant / total * 100) if total > 0 else 0,
            'average_score': round(avg_score, 2),
            'categories_distribution': categories,
            'top_category': max(categories.items(), key=lambda x: x[1])[0] if categories else None
        }

        return stats


if __name__ == "__main__":
    # Quick test
    import sys
    sys.path.append(str(Path(__file__).parent.parent.parent))

    from src.utils import setup_logging

    setup_logging()

    analyzer = ContentAnalyzer()

    # Analysis test
    test_contents = [
        {
            'title': 'GPT-5 Released with Major Improvements',
            'text': 'OpenAI announced GPT-5 today with significant improvements in reasoning capabilities...'
        },
        {
            'title': 'My cat is cute',
            'text': 'Just wanted to share a picture of my adorable cat.'
        },
        {
            'title': 'New Computer Vision Model Achieves SOTA',
            'text': 'Researchers published a new vision transformer model that achieves state-of-the-art results...'
        }
    ]

    results = analyzer.batch_analyze(test_contents)

    print("\nRésultats d'analyse:")
    for r in results:
        print(f"\n{r['title']}")
        print(f"  Pertinent: {r['is_relevant']} (Score: {r['relevance_score']}/10)")
        print(f"  Catégorie: {r['category']}")
        if r['insights']:
            print(f"  Insights: {r['insights'][:100]}...")

    stats = analyzer.get_statistics(results)
    print("\nStatistiques:")
    print(f"  Total: {stats['total_analyzed']}")
    print(f"  Pertinents: {stats['relevant_count']} ({stats['relevant_percentage']:.1f}%)")
    print(f"  Score moyen: {stats['average_score']}/10")
