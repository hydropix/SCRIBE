# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SCRIBE (Source Content Retrieval and Intelligence Bot Engine) is an automated AI intelligence gathering system that monitors Reddit and YouTube for AI-related content, analyzes it with a local LLM (Ollama), and generates daily Markdown reports with optional Discord notifications.

## Multi-Package Architecture

SCRIBE uses a **package-based architecture** where each package is an independent watch configuration. This allows running multiple, isolated intelligence gathering pipelines.

**Architecture:**
```
SCRIBE/
├── main.py                              # Orchestrator
├── packages/                            # Watch packages
│   └── ai_trends/                       # Example package
│       ├── settings.yaml                # Sources, thresholds, categories
│       └── prompts.yaml                 # LLM prompts
├── config/
│   └── global.yaml                      # Shared config (Ollama model)
├── src/
│   ├── package_manager.py               # Package discovery & loading
│   ├── collectors/                      # Reddit, YouTube collectors
│   ├── processors/                      # Ollama analysis, deduplication
│   ├── storage/                         # Cache, report generation
│   └── notifiers/                       # Discord webhooks
├── data/
│   └── ai_trends/                       # Package-specific data
│       ├── cache.db
│       ├── reports/
│       └── raw_logs/
└── logs/
    └── ai_trends.log                    # Package-specific logs
```

**9-Step Pipeline:**
1. Cache cleanup (90-day retention)
2. Data collection (Reddit via PRAW, YouTube via Google API)
3. Content preparation (unified format)
4. Cache filtering (skip processed items)
5. LLM analysis (Ollama scores relevance 1-10)
6. Relevance filtering (threshold: 7/10)
7. Deduplication (TF-IDF + SimHash similarity detection)
8. Report generation (Markdown + Discord notification)
9. **Optional:** Discord summary notification (concise <2000 chars to separate webhook)

## Common Commands

```bash
# List available packages
python main.py --list-packages

# Run a specific package
python main.py --package ai_trends --mode once

# Run with specific language
python main.py --package ai_trends --mode once --lang fr

# Show cache statistics
python main.py --package ai_trends --mode stats

# Verify API connections
python tests/test_connections.py

# Test Discord message splitting
python tests/test_discord_split.py
```

## Environment Setup

```bash
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
cp .env.example .env
# Edit .env with credentials
```

## Configuration

**`.env`** - API credentials and package-specific webhooks:
```bash
# Global APIs
REDDIT_CLIENT_ID=...
REDDIT_CLIENT_SECRET=...
YOUTUBE_API_KEY=...
OLLAMA_HOST=http://localhost:11434

# Package-specific webhooks
DISCORD_AI_TRENDS_WEBHOOK=...
DISCORD_AI_TRENDS_SUMMARY_WEBHOOK=...
```

**`config/global.yaml`** - Shared LLM settings:
- Model: qwen3:14b (or mistral, phi4, llama3, etc.)
- Context window: 32768 tokens
- Temperature: 0.3

**`packages/<name>/settings.yaml`** - Package configuration:
- Package metadata (name, display_name, description)
- Reddit: subreddits list, posts_limit, comments_limit, timeframe
- YouTube: search keywords, channels, videos_per_source
- Analysis: relevance_threshold (default 7), similarity_threshold (0.85)
- Categories: AI-related categories
- Reporting: language, min_insights
- Discord: webhook_env references, rich_embeds, summary settings

**`packages/<name>/prompts.yaml`** - LLM system prompts:
- relevance_analyzer
- insight_extractor
- executive_summary
- daily_summary

## Key Patterns

**Logging:** Package-specific logs in `logs/<package_name>.log` via `src/utils.setup_package_logging()`

**Configuration:** Packages loaded via `PackageManager` from `src/package_manager.py`

**Content Structure:** Each item has id, source, title, text, url, timestamp, metadata (author/channel info)

**Error Handling:** Non-blocking for collectors and Discord (graceful degradation)

**Language Support:** 11 languages (en, fr, es, de, it, pt, nl, ru, zh, ja, ar) - reports generated in specified language

## Data Storage

Per-package isolation:
- **Cache:** `data/<package>/cache.db` (SQLite)
- **Reports:** `data/<package>/reports/<package>_report_{YYYY-MM-DD}.md`
- **Raw logs:** `data/<package>/raw_logs/`
- **App logs:** `logs/<package>.log`
- **Tests:** `tests/` - All test scripts (test_*.py)

## Creating a New Package

```bash
# 1. Copy existing package
cp -r packages/ai_trends packages/cybersecurity

# 2. Edit packages/cybersecurity/settings.yaml
#    - Update package metadata
#    - Change subreddits, keywords, channels
#    - Update categories
#    - Set webhook_env references

# 3. Edit packages/cybersecurity/prompts.yaml
#    - Adapt prompts for the new domain

# 4. Add webhooks to .env
DISCORD_CYBERSECURITY_WEBHOOK=...
DISCORD_CYBERSECURITY_SUMMARY_WEBHOOK=...

# 5. Run
python main.py --package cybersecurity --mode once
```

## Deduplication Strategy

Two-tiered fast approach (no heavy ML models):
1. **SimHash** - Locality-sensitive fingerprinting (threshold: 0.85)
2. **TF-IDF** - Cosine similarity with title weighting (40% title, 60% content)

## Adding New Sources

1. Create collector in `src/collectors/` following `RedditCollector`/`YouTubeCollector` pattern
2. Constructor must accept `config: dict` parameter
3. Return list of dicts with: id, source, title, text, url, timestamp, metadata
4. Register in `main.py` SCRIBE class `_init_package_mode()`
5. Add to collection step in `run_veille()`

## Ollama Integration

- Wrapper: `src/processors/ollama_client.py`
- Analysis: JSON output with pertinent (bool), score (1-10), raison, categorie
- Insight extraction: translated_title, hook (teaser), insights (markdown)
- Daily summary: Concise <2000 char summary for Discord (optional feature)
- Prompts defined in `packages/<name>/prompts.yaml` under `system_prompts`

## Discord Notifications

**Main Notification (Step 8):**
- Rich embeds with images (Reddit posts + YouTube thumbnails)
- Detailed insights per category
- Webhook configured via `webhook_env` in package settings

**Summary Notification (Step 9, Optional):**
- Concise daily summary (<2000 chars)
- AI-generated overview of all insights
- Separate webhook via `summary.webhook_env` in package settings
- Enable via package settings: `discord.summary.enabled: true`

## Testing

**All test scripts must be placed in the `tests/` directory.**

Naming convention: `test_*.py`

```bash
# Run specific test
python tests/test_connections.py
python tests/test_discord_split.py

# Available tests:
# - test_connections.py - Verify API connections (Reddit, YouTube, Ollama, Discord)
# - test_discord_split.py - Test Discord message splitting
# - test_discord_images.py - Test Discord image embeds
# - test_similarity_real_data.py - Test deduplication with real data
```
