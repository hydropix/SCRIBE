"""Shared utilities for the SCRIBE intelligence system"""

import os
import yaml
import logging
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """Configure the logging system"""

    # Create logs folder if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Configure logger with UTF-8 encoding
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / "scribe.log", encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

    return logging.getLogger("SCRIBE")


def load_config(config_path: str) -> Dict[str, Any]:
    """Load a YAML configuration file"""

    config_file = Path(config_path)

    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_file, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    return config


def load_env_variables():
    """Load environment variables from .env"""

    env_path = Path(".env")

    if not env_path.exists():
        raise FileNotFoundError(
            ".env file not found. Please copy .env.example to .env and fill in your credentials."
        )

    load_dotenv(env_path, override=True)


def get_project_root() -> Path:
    """Return the project root path"""
    return Path(__file__).parent.parent


def ensure_directories():
    """Create necessary directories if they don't exist"""

    root = get_project_root()

    directories = [
        root / "data",
        root / "data" / "reports",
        root / "logs",
    ]

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)


def sanitize_filename(text: str, max_length: int = 100) -> str:
    """Clean text to make it a valid filename"""

    # Replace problematic characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        text = text.replace(char, '_')

    # Limit length
    text = text[:max_length]

    # Remove leading/trailing spaces
    text = text.strip()

    return text


def get_raw_logs_dir() -> Path:
    """Return the raw logs directory path"""
    return get_project_root() / "data" / "raw_logs"


def clear_raw_logs():
    """Delete all files in the raw logs directory"""
    raw_logs_dir = get_raw_logs_dir()

    if raw_logs_dir.exists():
        for file in raw_logs_dir.glob("*.md"):
            file.unlink()
    else:
        raw_logs_dir.mkdir(parents=True, exist_ok=True)


def save_raw_data_log(data: list, source: str, timestamp: str = None):
    """Save raw collected data to markdown files

    Args:
        data: List of raw data dictionaries
        source: Source name (e.g., 'reddit', 'youtube')
        timestamp: Optional timestamp string, defaults to current datetime
    """
    import json
    from datetime import datetime as dt

    if timestamp is None:
        timestamp = dt.now().strftime('%Y-%m-%d_%H-%M-%S')

    raw_logs_dir = get_raw_logs_dir()
    raw_logs_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{source}_raw_{timestamp}.md"
    filepath = raw_logs_dir / filename

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(f"# Raw Data - {source.upper()}\n")
        f.write(f"**Timestamp:** {timestamp}\n")
        f.write(f"**Total items:** {len(data)}\n\n")
        f.write("---\n\n")

        for i, item in enumerate(data, 1):
            f.write(f"## Item {i}\n\n")

            # Format based on source type
            if source == 'reddit':
                f.write(f"### {item.get('title', 'No title')}\n\n")
                f.write(f"**ID:** {item.get('id', 'N/A')}\n")
                f.write(f"**Subreddit:** r/{item.get('subreddit', 'N/A')}\n")
                f.write(f"**Author:** u/{item.get('author', 'N/A')}\n")
                f.write(f"**Score:** {item.get('score', 0)}\n")
                f.write(f"**Upvote Ratio:** {item.get('upvote_ratio', 0)}\n")
                f.write(f"**Comments:** {item.get('num_comments', 0)}\n")
                f.write(f"**Created:** {item.get('created_utc', 'N/A')}\n")
                f.write(f"**URL:** {item.get('permalink', item.get('url', 'N/A'))}\n")
                f.write(f"**Flair:** {item.get('link_flair_text', 'None')}\n\n")

                if item.get('selftext'):
                    f.write("#### Post Content\n\n")
                    f.write(f"```\n{item.get('selftext', '')}\n```\n\n")

                if item.get('comments'):
                    f.write("#### Top Comments\n\n")
                    for j, comment in enumerate(item.get('comments', []), 1):
                        f.write(f"**Comment {j}** (Score: {comment.get('score', 0)})\n")
                        f.write(f"By u/{comment.get('author', 'N/A')}\n\n")
                        f.write(f"```\n{comment.get('body', '')}\n```\n\n")

            elif source == 'youtube':
                f.write(f"### {item.get('title', 'No title')}\n\n")
                f.write(f"**Video ID:** {item.get('video_id', 'N/A')}\n")
                f.write(f"**Channel:** {item.get('channel_title', 'N/A')}\n")
                f.write(f"**Published:** {item.get('published_at', 'N/A')}\n")
                f.write(f"**URL:** {item.get('url', 'N/A')}\n")
                f.write(f"**Source Query:** {item.get('source_query', 'N/A')}\n\n")

                if item.get('description'):
                    f.write("#### Description\n\n")
                    f.write(f"```\n{item.get('description', '')[:2000]}\n```\n\n")

                if item.get('transcript'):
                    f.write("#### Transcript\n\n")
                    # Truncate very long transcripts for readability
                    transcript = item.get('transcript', '')
                    if len(transcript) > 10000:
                        f.write(f"```\n{transcript[:10000]}\n\n[... transcript truncated at 10000 chars, total length: {len(transcript)} chars ...]\n```\n\n")
                    else:
                        f.write(f"```\n{transcript}\n```\n\n")
            else:
                # Generic format for other sources
                f.write("```json\n")
                f.write(json.dumps(item, indent=2, default=str, ensure_ascii=False))
                f.write("\n```\n\n")

            f.write("---\n\n")

    return filepath
