# src/package_manager.py

"""
Package Manager for SCRIBE multi-package support.
Handles discovery, loading, and validation of watch packages.
"""

import os
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

import yaml
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("SCRIBE.PackageManager")


class PackageConfig:
    """Configuration holder for a single package."""

    def __init__(self, name: str, settings: Dict, prompts: Dict, global_config: Dict):
        self.name = name
        self.settings = settings
        self.prompts = prompts
        self.global_config = global_config

        # Derived paths
        self.data_dir = Path("data") / name
        self.cache_path = self.data_dir / "cache.db"
        self.reports_dir = self.data_dir / "reports"
        self.raw_logs_dir = self.data_dir / "raw_logs"
        self.log_file = Path("logs") / f"{name}.log"

        # Package metadata
        package_meta = settings.get("package", {})
        self.display_name = package_meta.get("display_name", name)
        self.description = package_meta.get("description", "")

    def get_discord_webhook(self) -> Optional[str]:
        """Get the main Discord webhook URL from environment."""
        discord_config = self.settings.get("discord", {})
        webhook_env = discord_config.get("webhook_env", f"DISCORD_{self.name.upper()}_WEBHOOK")
        return os.getenv(webhook_env)

    def get_discord_summary_webhook(self) -> Optional[str]:
        """Get the summary Discord webhook URL from environment."""
        discord_config = self.settings.get("discord", {})
        summary_config = discord_config.get("summary", {})
        webhook_env = summary_config.get("webhook_env", f"DISCORD_{self.name.upper()}_SUMMARY_WEBHOOK")
        return os.getenv(webhook_env)

    def get_ollama_config(self) -> Dict:
        """Get Ollama configuration (global + package overrides)."""
        ollama_global = self.global_config.get("ollama", {})
        ollama_package = self.settings.get("ollama", {})
        return {**ollama_global, **ollama_package}

    def get_system_prompt(self, prompt_name: str) -> str:
        """Get a system prompt by name."""
        return self.prompts.get("system_prompts", {}).get(prompt_name, "")

    def ensure_directories(self):
        """Create all required directories for this package."""
        directories = [
            self.data_dir,
            self.reports_dir,
            self.raw_logs_dir,
            self.log_file.parent
        ]
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Ensured directories for package: {self.name}")


class PackageManager:
    """Manages discovery and loading of SCRIBE packages."""

    def __init__(self, packages_dir: str = "packages", config_dir: str = "config"):
        self.packages_dir = Path(packages_dir)
        self.config_dir = Path(config_dir)
        self.global_config = self._load_global_config()
        self._packages_cache: Dict[str, PackageConfig] = {}

    def _load_global_config(self) -> Dict:
        """Load global configuration shared by all packages."""
        global_path = self.config_dir / "global.yaml"
        if global_path.exists():
            with open(global_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        logger.warning(f"Global config not found at {global_path}, using defaults")
        return {
            "ollama": {
                "model": "qwen3:14b",
                "context_window": 32768,
                "temperature": 0.3
            }
        }

    def list_packages(self) -> List[str]:
        """List all available package names."""
        if not self.packages_dir.exists():
            return []

        packages = []
        for item in self.packages_dir.iterdir():
            if item.is_dir() and (item / "settings.yaml").exists():
                packages.append(item.name)

        return sorted(packages)

    def load_package(self, package_name: str) -> PackageConfig:
        """Load a specific package configuration."""
        if package_name in self._packages_cache:
            return self._packages_cache[package_name]

        package_dir = self.packages_dir / package_name

        if not package_dir.exists():
            raise ValueError(f"Package '{package_name}' not found in {self.packages_dir}")

        # Load settings.yaml
        settings_path = package_dir / "settings.yaml"
        if not settings_path.exists():
            raise ValueError(f"settings.yaml not found in package '{package_name}'")

        with open(settings_path, 'r', encoding='utf-8') as f:
            settings = yaml.safe_load(f) or {}

        # Load prompts.yaml
        prompts_path = package_dir / "prompts.yaml"
        prompts = {}
        if prompts_path.exists():
            with open(prompts_path, 'r', encoding='utf-8') as f:
                prompts = yaml.safe_load(f) or {}
        else:
            logger.warning(f"prompts.yaml not found for package '{package_name}'")

        # Create PackageConfig
        config = PackageConfig(
            name=package_name,
            settings=settings,
            prompts=prompts,
            global_config=self.global_config
        )

        # Ensure directories exist
        config.ensure_directories()

        # Cache it
        self._packages_cache[package_name] = config

        logger.info(f"Loaded package: {config.display_name} ({package_name})")
        return config

    def get_package_info(self, package_name: str) -> Dict[str, Any]:
        """Get summary information about a package."""
        config = self.load_package(package_name)

        return {
            "name": config.name,
            "display_name": config.display_name,
            "description": config.description,
            "sources": {
                "reddit_subreddits": len(config.settings.get("reddit", {}).get("subreddits", [])),
                "youtube_channels": len(config.settings.get("youtube", {}).get("channels", [])),
                "youtube_keywords": len(config.settings.get("youtube", {}).get("keywords", []))
            },
            "categories": len(config.settings.get("analysis", {}).get("categories", [])),
            "language": config.settings.get("reports", {}).get("language", "en"),
            "discord_enabled": config.settings.get("discord", {}).get("enabled", False)
        }

    def validate_package(self, package_name: str) -> List[str]:
        """Validate a package configuration and return list of issues."""
        issues = []

        try:
            config = self.load_package(package_name)
        except Exception as e:
            return [f"Failed to load package: {str(e)}"]

        # Check required sections
        required_sections = ["reddit", "youtube", "analysis", "reports"]
        for section in required_sections:
            if section not in config.settings:
                issues.append(f"Missing required section: {section}")

        # Check Discord webhook if enabled
        if config.settings.get("discord", {}).get("enabled", False):
            if not config.get_discord_webhook():
                webhook_env = config.settings.get("discord", {}).get(
                    "webhook_env",
                    f"DISCORD_{package_name.upper()}_WEBHOOK"
                )
                issues.append(f"Discord enabled but {webhook_env} not set in .env")

        # Check prompts
        required_prompts = ["relevance_analyzer", "insight_extractor"]
        for prompt in required_prompts:
            if not config.get_system_prompt(prompt):
                issues.append(f"Missing required prompt: {prompt}")

        return issues
