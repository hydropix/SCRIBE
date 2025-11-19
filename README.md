<div align="center">
  <img src="SCRIBE_Logo.png" alt="SCRIBE Logo" width="600"/>

  ### Source Content Retrieval and Intelligence Bot Engine

  *Automated Multi-Topic Intelligence Gathering System*
</div>

---

## What is SCRIBE?

SCRIBE is an **automated monitoring bot** that watches Reddit and YouTube, analyzes content with a local AI (Ollama), and generates daily reports. It uses a **package-based architecture** allowing you to monitor multiple topics independently.

**In short:** You create a package for your topic → SCRIBE collects → AI analyzes → You receive a Markdown report (+ optional Discord notification).

---

## Key Features

- **Multi-package architecture** - Monitor multiple topics independently (AI, cybersecurity, gaming, etc.)
- **Multi-source** - Reddit and YouTube with customizable sources per package
- **Local AI** - Uses Ollama (Mistral, Phi4, Llama3, Qwen3...) - no cloud API needed
- **Smart deduplication** - Semantic detection of similar content (TF-IDF + SimHash)
- **Professional reports** - Structured Markdown with insights and metrics
- **Discord notifications** - Rich embeds with images + optional daily summary
- **SQLite cache** - Per-package isolation, avoids reprocessing
- **Multilingual** - Reports in 11 languages (en, fr, es, de, it, pt, nl, ru, zh, ja, ar)

---

## How Does It Work?

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   REDDIT    │     │   YOUTUBE   │     │   DISCORD   │
│    subs     │     │ transcripts │     │   webhook   │
└──────┬──────┘     └──────┬──────┘     └──────▲──────┘
       │                   │                   │
       └─────────┬─────────┘                   │
                 ▼                             │
        ┌─────────────────┐                    │
        │   1. COLLECT    │                    │
        │   Posts/Videos  │                    │
        └────────┬────────┘                    │
                 ▼                             │
        ┌─────────────────┐                    │
        │   2. FILTER     │                    │
        │  (SQLite Cache) │                    │
        └────────┬────────┘                    │
                 ▼                             │
        ┌─────────────────┐                    │
        │  3. AI ANALYSIS │                    │
        │      (LLM)      │                    │
        │  Score 1-10     │                    │
        │  Category       │                    │
        │  Insights       │                    │
        └────────┬────────┘                    │
                 ▼                             │
        ┌─────────────────┐                    │
        │ 4. DEDUPLICATE  │                    │
        │   (Semantic)    │                    │
        └────────┬────────┘                    │
                 ▼                             │
        ┌─────────────────┐                    │
        │   5. REPORT     │────────────────────┘
        │   (Markdown)    │
        └─────────────────┘
```

### The 9-Step Pipeline

1. **Cache cleanup** - 90-day retention policy
2. **Data collection** - Reddit posts + YouTube videos with transcripts
3. **Content preparation** - Unified format for all sources
4. **Cache filtering** - Skip already processed content
5. **AI Analysis** - Ollama scores relevance (1-10), categorizes, extracts insights
6. **Relevance filtering** - Keep only score >= threshold (default: 7/10)
7. **Deduplicate** - Semantic duplicate detection (TF-IDF + SimHash)
8. **Report** - Generate Markdown + Discord notification with rich embeds
9. **Summary** - Optional concise daily summary to separate Discord webhook

---

## Quick Installation

### Prerequisites

- **Python 3.10+**
- **Ollama** installed and running
- **Git** (for automatic updates)

### 1. Install Ollama

```bash
# Download from https://ollama.ai/
# Then:
ollama pull qwen3:14b  # or mistral, phi4, llama3
```

### 2. Clone and Setup

```bash
git clone https://github.com/your-repo/SCRIBE.git
cd SCRIBE
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
cp .env.example .env
```

### 3. Configure Your Credentials

Edit the `.env` file with your API keys:

```env
# Reddit (https://reddit.com/prefs/apps)
REDDIT_CLIENT_ID=your_id
REDDIT_CLIENT_SECRET=your_secret
REDDIT_USER_AGENT=SCRIBE/1.0

# YouTube (https://console.cloud.google.com/)
YOUTUBE_API_KEY=your_key

# Ollama
OLLAMA_HOST=http://localhost:11434

# Package-specific Discord webhooks
DISCORD_AI_TRENDS_WEBHOOK=your_webhook
DISCORD_AI_TRENDS_SUMMARY_WEBHOOK=your_summary_webhook
```

**Note**: Without Reddit/YouTube credentials, the app will still work but without those sources.

---

## Usage

### List Available Packages

```bash
python main.py --list-packages
```

### Run a Specific Package

```bash
python main.py --package ai_trends --mode once
```

The report will be generated in `data/ai_trends/reports/`.

### Run with Specific Language

```bash
python main.py --package ai_trends --mode once --lang en  # English
python main.py --package ai_trends --mode once --lang fr  # French
```

### View Package Statistics

```bash
python main.py --package ai_trends --mode stats
```

Shows: processed content, relevance rate, breakdown by source/category.

### Verify API Connections

```bash
python tests/test_connections.py
```

---

## Creating a New Package

SCRIBE's package system allows you to create independent monitoring configurations for any topic.

### 1. Copy an Existing Package

```bash
cp -r packages/ai_trends packages/cybersecurity
```

### 2. Edit Package Settings

**`packages/cybersecurity/settings.yaml`**:

```yaml
package:
  name: cybersecurity
  display_name: "Cybersecurity Watch"
  description: "Monitor cybersecurity news and threats"

reddit:
  subreddits:
    - netsec
    - cybersecurity
    - hacking
    - ReverseEngineering
  posts_limit: 10
  comments_limit: 5
  timeframe: "day"

youtube:
  keywords:
    - "cybersecurity news"
    - "malware analysis"
  channels:
    - "@JohnHammond"
    - "@LiveOverflow"
  videos_per_source: 5

analysis:
  relevance_threshold: 7
  similarity_threshold: 0.85

categories:
  - Malware Analysis
  - Vulnerability Research
  - Threat Intelligence
  - Network Security
  - Incident Response

reporting:
  language: "en"
  min_insights: 1

discord:
  webhook_env: "DISCORD_CYBERSECURITY_WEBHOOK"
  rich_embeds: true
  summary:
    enabled: true
    webhook_env: "DISCORD_CYBERSECURITY_SUMMARY_WEBHOOK"
```

### 3. Customize LLM Prompts

**`packages/cybersecurity/prompts.yaml`**:

Adapt the system prompts for your domain:
- `relevance_analyzer` - How to score content relevance
- `insight_extractor` - How to extract key insights
- `executive_summary` - How to write the report summary
- `daily_summary` - How to write the Discord summary

### 4. Add Webhooks to .env

```bash
DISCORD_CYBERSECURITY_WEBHOOK=https://discord.com/api/webhooks/...
DISCORD_CYBERSECURITY_SUMMARY_WEBHOOK=https://discord.com/api/webhooks/...
```

### 5. Run Your New Package

```bash
python main.py --package cybersecurity --mode once
```

---

## Configuration

### Global Settings (config/global.yaml)

Shared configuration for all packages:

```yaml
ollama:
  model: "qwen3:14b"  # or mistral, phi4, llama3
  parameters:
    temperature: 0.3
    num_ctx: 32768
```

### Package Settings (packages/<name>/settings.yaml)

Each package has its own:
- **Sources** - Subreddits, YouTube channels/keywords
- **Thresholds** - Relevance score, similarity detection
- **Categories** - Domain-specific classification
- **Discord** - Separate webhooks per package

---

## Discord Notifications

### Main Notification (Step 8)

- Rich embeds with images (Reddit posts + YouTube thumbnails)
- Detailed insights per category
- Configured via `discord.webhook_env` in package settings

### Summary Notification (Step 9, Optional)

- Concise AI-generated overview (<2000 chars)
- Sent to separate webhook
- Enable in package settings:

```yaml
discord:
  summary:
    enabled: true
    webhook_env: "DISCORD_AI_TRENDS_SUMMARY_WEBHOOK"
```

---

## Daily Scheduler (Windows)

To run SCRIBE automatically every day:

### Using Task Scheduler GUI

1. Press **Win + R**, type `taskschd.msc`, press Enter
2. Click **Create Basic Task**
3. **Name**: "SCRIBE AI Trends" → Next
4. **Trigger**: Daily at your preferred time → Next
5. **Action**: Start a program
6. **Program**: `python`
7. **Arguments**: `main.py --package ai_trends --mode once`
8. **Start in**: `C:\path\to\SCRIBE`

### Command Line

```powershell
schtasks /create /tn "SCRIBE AI Trends" /tr "python main.py --package ai_trends --mode once" /sc daily /st 08:00
```

---

## Generated Report Example

```markdown
# SCRIBE - CYBERSECURITY INTELLIGENCE REPORT
## 2025-01-15 | 08:00

New ransomware variants targeting critical infrastructure
detected this week, with increased activity from APT groups...

## Malware Analysis
   3 insight(s)

### 1. New Ransomware Strain Targets Healthcare
**Source**: Reddit
**Link**: https://reddit.com/r/netsec/...
**Relevance**: 9/10
**Author**: u/malware_analyst

**Insights**: A new ransomware variant has been discovered
targeting healthcare systems with sophisticated evasion...

---

## Threat Intelligence
   2 insight(s)

### 1. APT Group Activity Analysis
**Source**: YouTube
**Link**: https://youtube.com/watch?v=...
**Relevance**: 8/10

**Insights**: Detailed breakdown of recent APT campaign...

---

*Report generated by SCRIBE - 5 total insights*
```

---

## Troubleshooting

### "Model not found"

```bash
ollama list              # View installed models
ollama pull qwen3:14b    # Install missing model
```

### "Package not found"

```bash
python main.py --list-packages  # List available packages
```

Ensure your package directory exists in `packages/` with valid `settings.yaml`.

### "Reddit credentials invalid"

Check that your `.env` contains the correct values from https://reddit.com/prefs/apps

### "YouTube quota exceeded"

YouTube API has a free daily limit. Reduce `videos_per_source` in your package settings.

### Ollama too slow

- Use a lighter model (phi4 vs qwen3:14b)
- Reduce content limits in package settings

### Not enough insights

- Lower `relevance_threshold` (e.g., 5 instead of 7)
- Increase `posts_limit` or `videos_per_source`
- Add more subreddits/channels

---

## Testing

All tests are in the `tests/` directory:

```bash
python tests/test_connections.py       # Verify API connections
python tests/test_discord_split.py     # Test Discord message splitting
python tests/test_discord_images.py    # Test Discord image embeds
```

---

## Logs

Per-package logging:

- **Application**: `logs/<package_name>.log`
- **Raw data**: `data/<package_name>/raw_logs/`

---

## Adding New Collectors

1. Create collector in `src/collectors/` following existing patterns
2. Constructor must accept `config: dict`
3. Return list of dicts with: `id`, `source`, `title`, `text`, `url`, `timestamp`, `metadata`
4. Register in `main.py` SCRIBE class

---

## Roadmap

- [x] Reddit and YouTube collection
- [x] Local AI analysis (Ollama)
- [x] Semantic deduplication
- [x] Markdown reports
- [x] Discord notifications with rich embeds
- [x] Multi-package architecture
- [x] Per-package Discord webhooks
- [x] Daily summary feature
- [ ] Emerging trend detection

---

## Contributing

The project is designed to be extensible:

- Add packages: `packages/<your_topic>/`
- Add sources: `src/collectors/`
- New processors: `src/processors/`
- Report templates: `src/storage/report_generator.py`

---

## License

MIT License - Free to use and modify

---

<div align="center">
  <b>SCRIBE - Your Automated Multi-Topic Intelligence Assistant</b>
</div>
