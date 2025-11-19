# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SCRIBE (Source Content Retrieval and Intelligence Bot Engine) is an automated AI intelligence gathering system that monitors Reddit and YouTube for AI-related content, analyzes it with a local LLM (Ollama), and generates daily Markdown reports with optional Discord notifications.

## Architecture

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

**Key Components:**
- `main.py` - Orchestrator class `SCRIBE` coordinating entire workflow
- `src/collectors/` - Reddit and YouTube data fetchers
- `src/processors/` - Ollama analysis, deduplication, similarity detection
- `src/storage/` - SQLite cache and Markdown report generation
- `src/notifiers/` - Discord webhook integration
- `config/settings.yaml` - Sources, categories, thresholds
- `config/ollama_config.yaml` - LLM model parameters and system prompts

## Common Commands

```bash
# Run single collection cycle
python main.py --mode once

# Run with specific language
python main.py --mode once --lang fr
python main.py --mode once --lang en

# Show cache statistics
python main.py --mode stats

# Verify API connections
python tests/test_connections.py

# Test Discord message splitting
python tests/test_discord_split.py

# Windows auto-setup and run
quick_start.bat
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

**`.env`** - API credentials (Reddit, YouTube, Ollama host, Discord webhooks: main + optional summary)

**`config/settings.yaml`** - Collection parameters:
- Reddit: subreddits list, posts_limit, comments_limit, timeframe
- YouTube: search keywords, channels, videos_per_source
- Analysis: relevance_threshold (default 7), similarity_threshold (0.85)
- Categories: 22 AI-related categories
- Reporting: output directory, minimum insights, default language
- Discord: rich_embeds, summary settings (enabled, max_length, mention_role)

**`config/ollama_config.yaml`** - LLM settings:
- Model: qwen3:14b (or mistral, phi4, llama3, etc.)
- Context window: 32768 tokens
- Temperature: 0.3
- System prompts for: relevance_analyzer, insight_extractor, executive_summary, daily_summary

## Key Patterns

**Logging:** Hierarchical logger names (`SCRIBE.ComponentName`), outputs to `logs/scribe.log` and console via `src/utils.setup_logging()`

**Configuration:** Load from YAML via `src/utils.load_config()`, supports runtime overrides

**Content Structure:** Each item has id, source, title, text, url, timestamp, metadata (author/channel info)

**Error Handling:** Non-blocking for collectors and Discord (graceful degradation)

**Language Support:** 11 languages (en, fr, es, de, it, pt, nl, ru, zh, ja, ar) - reports generated in specified language

## Data Storage

- **Cache:** `data/cache.db` (SQLite) - processed content and generated reports
- **Reports:** `data/reports/veille_ia_{YYYY-MM-DD}.md`
- **Raw logs:** `data/raw_logs/reddit_*.md`, `data/raw_logs/youtube_*.md`
- **App logs:** `logs/scribe.log`
- **Tests:** `tests/` - All test scripts (test_*.py)

## Deduplication Strategy

Two-tiered fast approach (no heavy ML models):
1. **SimHash** - Locality-sensitive fingerprinting (threshold: 0.85)
2. **TF-IDF** - Cosine similarity with title weighting (40% title, 60% content)

## Adding New Sources

1. Create collector in `src/collectors/` following `RedditCollector`/`YouTubeCollector` pattern
2. Return list of dicts with: id, source, title, text, url, timestamp, metadata
3. Register in `main.py` SCRIBE class initialization
4. Add to collection step in `run_veille()`

## Ollama Integration

- Wrapper: `src/processors/ollama_client.py`
- Analysis: JSON output with pertinent (bool), score (1-10), raison, categorie
- Insight extraction: translated_title, hook (teaser), insights (markdown)
- Daily summary: Concise <2000 char summary for Discord (optional feature)
- Prompts defined in `config/ollama_config.yaml` under `system_prompts`

## Discord Notifications

**Main Notification (Step 8):**
- Rich embeds with images (Reddit posts + YouTube thumbnails)
- Detailed insights per category
- Sent to `DISCORD_WEBHOOK_URL`

**Summary Notification (Step 9, Optional):**
- Concise daily summary (<2000 chars)
- AI-generated overview of all insights
- Sent to separate webhook: `DISCORD_SUMMARY_WEBHOOK_URL`
- Enable via `config/settings.yaml`: `discord.summary.enabled: true`
- See `DISCORD_SUMMARY.md` for setup guide

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
