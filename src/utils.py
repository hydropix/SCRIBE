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

    load_dotenv(env_path)


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
