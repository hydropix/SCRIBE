"""Markdown report generator for monitoring"""

import logging
from typing import List, Dict, Any
from datetime import datetime
from pathlib import Path

from src.processors.ollama_client import OllamaClient


class ReportGenerator:
    """Generates monitoring reports in Markdown format"""

    def __init__(
        self,
        package_name: str,
        config: dict,
        prompts: dict = None,
        ollama_config: dict = None,
        language: str = None,
        package_display_name: str = None
    ):
        """
        Initializes the report generator

        Args:
            package_name: Name of the package (for report naming)
            config: Configuration dict from package
            prompts: Prompts dict from package
            ollama_config: Ollama model configuration
            language: Language for report generation (overrides config if provided)
            package_display_name: Display name of the package for report header
        """
        self.logger = logging.getLogger("SCRIBE.ReportGenerator")
        self.config = config
        self.prompts = prompts or {}
        self.package_name = package_name
        self.package_display_name = package_display_name or package_name.replace('_', ' ').title()
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
        self.ollama = OllamaClient(config=ollama_config, prompts=self.prompts, language=language)
        self.language = language

        # Output directory based on package
        self.output_dir = Path("data") / package_name / "reports"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.logger.info(f"Report generator initialized (package: {self.package_name}, language: {language})")

    def generate_report(
        self,
        relevant_contents: List[Dict[str, Any]],
        report_date: str = None,
        statistics: Dict[str, Any] = None,
        debug_messages: List[str] = None
    ) -> Dict[str, Any]:
        """
        Generates a complete monitoring report

        Args:
            relevant_contents: List of relevant analyzed contents
            report_date: Report date (default today)
            statistics: Collection statistics (optional)
            debug_messages: Optional list of debug/error messages to append to report

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
            statistics,
            debug_messages
        )

        # Save with package-specific filename
        report_filename = f"{self.package_name}_report_{report_date}.md"
        report_path = self.output_dir / report_filename

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
        statistics: Dict[str, Any] = None,
        debug_messages: List[str] = None
    ) -> str:
        """Builds the Markdown content of the report"""

        # Header with date integrated in title
        current_datetime = datetime.now()
        formatted_date = current_datetime.strftime('%d %B %Y')

        lines = [
            f"# 📊 {self.package_display_name.upper()} - {formatted_date}",
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

        # Debug messages section (if any)
        if debug_messages:
            lines.extend([
                "",
                "## ⚠️ Debug Information",
                "",
            ])
            for msg in debug_messages:
                lines.append(msg)
                lines.append("")

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

        # Add hidden metadata as HTML comment for fallback parsing
        metadata = content.get('metadata', {})
        hidden_meta = []
        if metadata.get('source'):
            hidden_meta.append(f"source={metadata['source']}")
        if metadata.get('video_id'):
            hidden_meta.append(f"video_id={metadata['video_id']}")
        if metadata.get('image_url'):
            hidden_meta.append(f"image_url={metadata['image_url']}")
        if metadata.get('subreddit'):
            hidden_meta.append(f"subreddit={metadata['subreddit']}")
        if hidden_meta:
            lines.append(f"<!-- {' | '.join(hidden_meta)} -->")
            lines.append("")

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

        # Join metadata with line breaks
        if metadata_parts:
            lines.append("📎 **Metadata**")
            for part in metadata_parts:
                lines.append(f"  - {part}")
            lines.append("")

        lines.append("")

        return lines


if __name__ == "__main__":
    # Quick test
    import sys
    sys.path.append(str(Path(__file__).parent.parent.parent))

    from src.utils import setup_package_logging
    from src.package_manager import PackageManager

    setup_package_logging("test")

    # Load config from package
    pm = PackageManager()
    pkg = pm.load_package("ai_trends")

    generator = ReportGenerator(
        package_name=pkg.name,
        config=pkg.settings,
        prompts=pkg.prompts,
        ollama_config=pkg.get_ollama_config()
    )

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
