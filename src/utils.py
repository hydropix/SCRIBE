"""Shared utilities for the SCRIBE intelligence system"""

import os
import yaml
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv


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


def setup_package_logging(package_name: str, level: str = "INFO") -> logging.Logger:
    """Setup logging for a specific package.

    Args:
        package_name: Name of the package
        level: Logging level (INFO, DEBUG, etc.)

    Returns:
        Logger configured for the package
    """
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    log_file = log_dir / f"{package_name}.log"

    # Create package-specific logger
    logger = logging.getLogger(f"SCRIBE.{package_name}")
    logger.setLevel(getattr(logging, level.upper()))

    # Avoid duplicate handlers
    if not logger.handlers:
        # File handler
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        logger.addHandler(file_handler)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        logger.addHandler(console_handler)

    return logger


def get_package_data_dir(package_name: str) -> Path:
    """Get the data directory for a specific package.

    Args:
        package_name: Name of the package

    Returns:
        Path to the package data directory
    """
    return get_project_root() / "data" / package_name


def get_package_raw_logs_dir(package_name: str) -> Path:
    """Get the raw logs directory for a specific package.

    Args:
        package_name: Name of the package

    Returns:
        Path to the package raw logs directory
    """
    return get_package_data_dir(package_name) / "raw_logs"


def save_package_raw_data_log(package_name: str, data: list, source: str):
    """Save raw collected data to package-specific log file.

    Args:
        package_name: Name of the package
        data: List of raw data dictionaries
        source: Source name (e.g., 'reddit', 'youtube')

    Returns:
        Path to the saved file
    """
    import json

    raw_logs_dir = get_package_raw_logs_dir(package_name)
    raw_logs_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{source}_{timestamp}.md"
    filepath = raw_logs_dir / filename

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(f"# Raw Data - {source.upper()} - {package_name}\n")
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
                f.write(f"**URL:** {item.get('permalink', item.get('url', 'N/A'))}\n\n")

                if item.get('selftext'):
                    f.write("#### Post Content\n\n")
                    f.write(f"```\n{item.get('selftext', '')[:2000]}\n```\n\n")

            elif source == 'youtube':
                f.write(f"### {item.get('title', 'No title')}\n\n")
                f.write(f"**Video ID:** {item.get('video_id', 'N/A')}\n")
                f.write(f"**Channel:** {item.get('channel_title', 'N/A')}\n")
                f.write(f"**URL:** {item.get('url', 'N/A')}\n\n")

                if item.get('description'):
                    f.write("#### Description\n\n")
                    f.write(f"```\n{item.get('description', '')[:2000]}\n```\n\n")

            else:
                # Generic format for other sources
                f.write("```json\n")
                f.write(json.dumps(item, indent=2, default=str, ensure_ascii=False))
                f.write("\n```\n\n")

            f.write("---\n\n")

    return filepath
