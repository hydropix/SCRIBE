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

        # Generate executive summary
        executive_summary = self._generate_executive_summary(relevant_contents)

        # Build Markdown content
        markdown = self._build_markdown(
            report_date,
            executive_summary,
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
            'executive_summary': executive_summary,
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

    def _generate_executive_summary(
        self,
        contents: List[Dict[str, Any]]
    ) -> str:
        """Generates an executive summary with Ollama"""

        self.logger.info("Generating executive summary...")

        # Retrieve all insights
        all_insights = []
        for content in contents:
            if content.get('insights'):
                # Limit the size of each insight
                insight = f"- {content['title']}: {content['insights'][:200]}"
                all_insights.append(insight)

        # Limit the number of insights to avoid exceeding context
        if len(all_insights) > 30:
            all_insights = all_insights[:30]

        try:
            summary = self.ollama.generate_executive_summary(all_insights)
            return summary
        except Exception as e:
            self.logger.error(f"Error generating executive summary: {e}")
            return "Warning: Error generating executive summary."

    def _build_markdown(
        self,
        report_date: str,
        executive_summary: str,
        by_category: Dict[str, List[Dict[str, Any]]],
        statistics: Dict[str, Any] = None
    ) -> str:
        """Builds the Markdown content of the report"""

        lines = [
            f"# Veille IA - {report_date}",
            "",
            f"*Rapport généré automatiquement le {datetime.now().strftime('%Y-%m-%d à %H:%M')}*",
            "",
            "---",
            "",
        ]

        # Executive summary
        lines.extend([
            "## 📊 Résumé Exécutif",
            "",
            executive_summary,
            "",
            "---",
            "",
        ])

        # Statistics if available
        if statistics and self.report_config.get('include_metrics', True):
            lines.extend([
                "## 📈 Métriques",
                "",
                f"- **Total de contenus analysés**: {statistics.get('total_analyzed', 0)}",
                f"- **Contenus pertinents**: {statistics.get('relevant_count', 0)} ({statistics.get('relevant_percentage', 0):.1f}%)",
                f"- **Score de pertinence moyen**: {statistics.get('average_score', 0)}/10",
                f"- **Catégories couvertes**: {len(by_category)}",
                "",
            ])

            # Distribution by category
            if statistics.get('categories_distribution'):
                lines.append("**Distribution par catégorie**:")
                lines.append("")
                for cat, count in sorted(
                    statistics['categories_distribution'].items(),
                    key=lambda x: x[1],
                    reverse=True
                ):
                    lines.append(f"- {cat}: {count}")
                lines.append("")

            # Sources
            if 'by_source' in statistics:
                lines.append("**Sources**:")
                lines.append("")
                for source, count in statistics['by_source'].items():
                    lines.append(f"- {source.title()}: {count}")
                lines.append("")

            lines.extend(["", "---", ""])

        # Table of contents
        lines.extend([
            "## 📑 Table des Matières",
            "",
        ])

        for i, category in enumerate(by_category.keys(), 1):
            anchor = category.lower().replace(' ', '-').replace('&', 'and')
            lines.append(f"{i}. [{category}](#{anchor}) ({len(by_category[category])} insights)")

        lines.extend(["", "---", ""])

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

        lines = [
            f"### {index}. {content['title']}",
            "",
        ]

        # Metadata
        metadata = content.get('metadata', {})
        source = metadata.get('source', 'unknown').title()

        lines.append(f"**Source**: {source}")

        # Link
        url = metadata.get('url') or metadata.get('permalink')
        if url:
            lines.append(f"**Link**: [{url}]({url})")

        # Relevance score
        score = content.get('relevance_score', 0)
        lines.append(f"**Relevance**: {score}/10")

        # Author/Channel if available
        if metadata.get('author'):
            lines.append(f"**Auteur**: {metadata['author']}")
        elif metadata.get('channel_title'):
            lines.append(f"**Channel**: {metadata['channel_title']}")

        # Date
        if metadata.get('created_utc'):
            date_str = metadata['created_utc']
            if isinstance(date_str, datetime):
                date_str = date_str.strftime('%Y-%m-%d %H:%M')
            lines.append(f"**Date**: {date_str}")
        elif metadata.get('published_at'):
            lines.append(f"**Date**: {metadata['published_at'][:10]}")

        lines.append("")

        # Insights
        if content.get('insights'):
            lines.extend([
                "**Insights**:",
                "",
                content['insights'],
                "",
            ])

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
