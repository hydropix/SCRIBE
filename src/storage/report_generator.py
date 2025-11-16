"""Markdown report generator for monitoring"""

import logging
from typing import List, Dict, Any
from datetime import datetime
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.utils import load_config
from src.processors.ollama_client import OllamaClient


class ReportGenerator:
    """Generates monitoring reports in Markdown format"""

    def __init__(
        self,
        settings_path: str = "config/settings.yaml",
        ollama_config_path: str = "config/ollama_config.yaml",
        language: str = None
    ):
        """
        Initializes the report generator

        Args:
            settings_path: Path to settings.yaml
            ollama_config_path: Path to ollama_config.yaml
            language: Language for report generation (overrides config if provided)
        """
        self.logger = logging.getLogger("SCRIBE.ReportGenerator")
        self.config = load_config(settings_path)
        self.report_config = self.config.get('reports', {})

        # Get language from parameter or config (default: English)
        if language is None:
            language_code = self.report_config.get('language', 'en')
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

        # Ollama client for summaries with language support
        self.ollama = OllamaClient(ollama_config_path, language=language)
        self.language = language

        self.output_dir = Path(self.report_config.get('output_dir', 'data/reports'))
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.logger.info(f"Report generator initialized (language: {language})")

    def generate_report(
        self,
        relevant_contents: List[Dict[str, Any]],
        report_date: str = None,
        statistics: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Generates a complete monitoring report

        Args:
            relevant_contents: List of relevant analyzed contents
            report_date: Report date (default today)
            statistics: Collection statistics (optional)

        Returns:
            Dictionary containing:
                - path: Path to the generated report file
                - executive_summary: The generated executive summary
                - statistics: The statistics used in the report
        """
        if not relevant_contents:
            self.logger.warning("No relevant contents to generate report")
            return None

        # Report date
        if not report_date:
            report_date = datetime.now().strftime(
                self.report_config.get('date_format', '%Y-%m-%d')
            )

        self.logger.info(f"Generating report for {report_date}...")

        # Group by category
        by_category = self._group_by_category(relevant_contents)

        # Build Markdown content
        markdown = self._build_markdown(
            report_date,
            by_category,
            statistics
        )

        # Save
        report_path = self.output_dir / f"veille_ia_{report_date}.md"

        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(markdown)

        self.logger.info(f"Report generated: {report_path}")

        return {
            'path': str(report_path),
            'statistics': statistics
        }

    def _group_by_category(
        self,
        contents: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Groups contents by category"""

        grouped = {}

        for content in contents:
            category = content.get('category', 'Autre')

            if category not in grouped:
                grouped[category] = []

            grouped[category].append(content)

        # Sort by number of contents (descending)
        sorted_grouped = dict(
            sorted(grouped.items(), key=lambda x: len(x[1]), reverse=True)
        )

        return sorted_grouped

    def _build_markdown(
        self,
        report_date: str,
        by_category: Dict[str, List[Dict[str, Any]]],
        statistics: Dict[str, Any] = None
    ) -> str:
        """Builds the Markdown content of the report"""

        # Header impactant avec date et heure
        current_datetime = datetime.now()
        formatted_date = current_datetime.strftime('%d %B %Y')
        formatted_time = current_datetime.strftime('%H:%M')

        lines = [
            "# 📊 AI TRENDS & INNOVATIONS",
            "",
            "---",
            "",
            f"## 📅 {formatted_date} | ⏰ {formatted_time}",
            "",
            "---",
            "",
        ]

        # Contents by category
        for category, contents in by_category.items():
            lines.extend([
                f"## {category}",
                "",
                f"*{len(contents)} insight(s)*",
                "",
            ])

            for i, content in enumerate(contents, 1):
                lines.extend(self._format_content_item(content, i))

            lines.extend(["", "---", ""])

        # Footer
        lines.extend([
            "",
            "---",
            "",
            f"*Report generated by SCRIBE - {len(sum(by_category.values(), []))} insights total*",
            ""
        ])

        return "\n".join(lines)

    def _format_content_item(
        self,
        content: Dict[str, Any],
        index: int
    ) -> List[str]:
        """Formats a content item for Markdown"""

        # Use translated title if available, otherwise original title
        display_title = content.get('translated_title', content['title'])

        lines = [
            f"### {index}. {display_title}",
            "",
        ]

        # Hook (short teaser to engage reader)
        if content.get('hook'):
            lines.extend([
                f"*{content['hook']}*",
                "",
            ])

        # Insights (main content)
        if content.get('insights'):
            lines.extend([
                content['insights'],
                "",
            ])

        # Metadata at the end
        metadata = content.get('metadata', {})
        metadata_parts = []

        # Link
        url = metadata.get('url') or metadata.get('permalink')
        if url:
            metadata_parts.append(f"[Source]({url})")

        # Relevance score
        score = content.get('relevance_score', 0)
        metadata_parts.append(f"Relevance: {score}/10")

        # Author/Channel if available
        if metadata.get('author'):
            metadata_parts.append(f"Author: {metadata['author']}")
        elif metadata.get('channel_title'):
            metadata_parts.append(f"Channel: {metadata['channel_title']}")

        # Date
        if metadata.get('created_utc'):
            date_str = metadata['created_utc']
            if isinstance(date_str, datetime):
                date_str = date_str.strftime('%Y-%m-%d')
            metadata_parts.append(f"Date: {date_str}")
        elif metadata.get('published_at'):
            metadata_parts.append(f"Date: {metadata['published_at'][:10]}")

        # Join metadata with separator
        if metadata_parts:
            lines.append(f"📎 {' | '.join(metadata_parts)}")
            lines.append("")

        lines.append("")

        return lines


if __name__ == "__main__":
    # Quick test
    import sys
    sys.path.append(str(Path(__file__).parent.parent.parent))

    from src.utils import setup_logging

    setup_logging()

    generator = ReportGenerator()

    # Test contents
    test_contents = [
        {
            'title': 'GPT-5 Released',
            'translated_title': 'Sortie de GPT-5 : Une Révolution dans le Raisonnement IA',
            'hook': 'OpenAI repousse les limites du possible. Découvrez comment GPT-5 transforme notre rapport à l\'intelligence artificielle.',
            'is_relevant': True,
            'relevance_score': 9,
            'category': 'Large Language Models',
            'insights': 'OpenAI a lancé GPT-5 avec des capacités de raisonnement améliorées de 40%.',
            'metadata': {
                'source': 'reddit',
                'url': 'http://reddit.com/example',
                'author': 'user123',
                'created_utc': datetime.now()
            }
        },
        {
            'title': 'New Vision Transformer Architecture',
            'translated_title': 'Nouvelle Architecture Vision Transformer : Record Battu sur ImageNet',
            'hook': 'Les chercheurs viennent de franchir un cap décisif en vision par ordinateur.',
            'is_relevant': True,
            'relevance_score': 8,
            'category': 'Computer Vision',
            'insights': 'Nouvelle architecture ViT atteignant SOTA sur ImageNet.',
            'metadata': {
                'source': 'youtube',
                'url': 'http://youtube.com/watch?v=example',
                'channel_title': 'AI Research',
                'published_at': '2024-01-15T10:00:00Z'
            }
        }
    ]

    stats = {
        'total_analyzed': 100,
        'relevant_count': 2,
        'relevant_percentage': 2.0,
        'average_score': 5.5,
        'categories_distribution': {
            'Large Language Models': 1,
            'Computer Vision': 1
        },
        'by_source': {
            'reddit': 1,
            'youtube': 1
        }
    }

    result = generator.generate_report(test_contents, statistics=stats)
    print(f"\nGenerated report: {result['path']}")
    print(f"Executive summary: {result['executive_summary'][:100]}...")
