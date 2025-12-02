"""Content analyzer using Ollama for filtering and categorizing"""

import logging
from typing import Dict, Any, List

from src.processors.ollama_client import OllamaClient


class ContentAnalyzer:
    """Analyzes collected contents with Ollama"""

    def __init__(
        self,
        config: dict,
        prompts: dict = None,
        ollama_config: dict = None,
        language: str = None
    ):
        """
        Initializes the content analyzer

        Args:
            config: Package settings dict
            prompts: Package prompts dict
            ollama_config: Ollama model configuration
            language: Language for content analysis (overrides config if provided)
        """
        self.logger = logging.getLogger("SCRIBE.ContentAnalyzer")
        self.config = config
        self.prompts = prompts or {}
        self.analysis_config = self.config.get('analysis', {})

        # Get language from parameter or config (default: English)
        if language is None:
            report_config = self.config.get('reports', {})
            language_code = report_config.get('language', 'en')
            # Map language codes to full names
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
            language = language_map.get(language_code, 'English')

        # Initialize Ollama client with language support
        self.ollama = OllamaClient(
            config=ollama_config,
            prompts=self.prompts if isinstance(self.prompts, dict) and 'system_prompts' in self.prompts else {'system_prompts': self.prompts},
            language=language
        )

        self.relevance_threshold = self.analysis_config.get('relevance_threshold', 7)
        self.categories = self.analysis_config.get('categories', [])

        self.logger.info(f"Content analyzer initialized (language: {language})")

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

        # 1. Relevance analysis (pass metadata for context)
        relevance = self.ollama.analyze_relevance(content, title, metadata)

        # Check relevance threshold
        is_relevant = (
            relevance.get('relevant', False) and
            relevance.get('score', 0) >= self.relevance_threshold
        )

        result = {
            'title': title,
            'is_relevant': is_relevant,
            'relevance_score': relevance.get('score', 0),
            'relevance_reason': relevance.get('reason', ''),
            'category': relevance.get('category', 'Unknown'),
            'insights': None,
            'metadata': metadata
        }

        # 2. Extract insights if relevant
        if is_relevant:
            try:
                insights_data = self.ollama.extract_insights(content, title)
                # Store the full insights data (dict with translated_title, hook, insights)
                result['insights'] = insights_data.get('insights', '')
                result['translated_title'] = insights_data.get('translated_title', title)
                result['hook'] = insights_data.get('hook', '')
                self.logger.info(f"✓ Relevant ({relevance['score']}): {title[:60]}")
            except Exception as e:
                self.logger.error(f"Error extracting insights: {e}")
                result['insights'] = "Error extracting insights"
                result['translated_title'] = title
                result['hook'] = ''
        else:
            self.logger.debug(f"✗ Not relevant ({relevance['score']}): {title[:60]}")

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
        Filters to keep only relevant contents, sorted by score and limited to max_items

        Args:
            analysis_results: Analysis results

        Returns:
            Top relevant contents sorted by relevance score (descending)
        """
        # Filter by relevance
        relevant = [r for r in analysis_results if r['is_relevant']]

        # Sort by relevance score (descending) for best items first
        relevant.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)

        # Apply max_items limit if configured
        max_items = self.analysis_config.get('max_items')
        if max_items and len(relevant) > max_items:
            self.logger.info(
                f"Limiting to top {max_items} items (from {len(relevant)} relevant)"
            )
            relevant = relevant[:max_items]

        self.logger.info(
            f"Filtered: {len(relevant)}/{len(analysis_results)} relevant contents "
            f"(sorted by score, top scores: {[r.get('relevance_score', 0) for r in relevant[:5]]})"
        )

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
    from pathlib import Path
    import sys
    sys.path.append(str(Path(__file__).parent.parent.parent))

    from src.utils import setup_package_logging
    from src.package_manager import PackageManager

    setup_package_logging("test")

    # Load config from package
    pm = PackageManager()
    pkg = pm.load_package("ai_trends")

    analyzer = ContentAnalyzer(
        config=pkg.settings,
        prompts=pkg.prompts,
        ollama_config=pkg.get_ollama_config()
    )

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
