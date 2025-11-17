<div align="center">
  <img src="SCRIBE_Logo.png" alt="SCRIBE Logo" width="600"/>
  
  ### Source Content Retrieval and Intelligence Bot Engine

  *Automated AI Technology Intelligence System*
</div>

---

## What is SCRIBE?

SCRIBE is an **automated monitoring bot** that watches Reddit and YouTube for you, analyzes content with a local AI (Ollama), and generates daily reports on the latest artificial intelligence news.

**In short:** You configure your sources → SCRIBE collects → AI analyzes → You receive a Markdown report (+ optional Discord notification).

---

## How does it work?

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   REDDIT    │     │   YOUTUBE   │     │   DISCORD   │
│  (23 subs)  │     │ (transcripts)│    │  (webhook)  │
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
        │    (Ollama)     │                    │
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

### The 5 Steps in Detail

1. **Collect** - Fetches Reddit posts (title + comments) and YouTube videos (with full transcript)
2. **Filter** - Skips already processed content (SQLite database)
3. **AI Analysis** - Ollama evaluates each piece of content:
   - Relevance score (1-10)
   - Category (LLM, Robotics, AI Ethics, etc.)
   - Key points summary
4. **Deduplicate** - Removes semantic duplicates (not just identical titles)
5. **Report** - Generates a Markdown file organized by category with executive summary

---

## Features

- **Multi-source** : Reddit (23+ subreddits) and YouTube (channels + keywords)
- **Local AI** : Uses Ollama (Mistral, Phi4, Llama3...) - no cloud API needed
- **Smart deduplication** : Semantic detection of similar content
- **Professional reports** : Structured Markdown with insights and metrics
- **Discord notifications** : Automatic alerts with summary
- **SQLite cache** : Avoids reprocessing the same content
- **Multilingual** : Reports in English, French, Spanish, etc.

---

## Quick Installation

### Prerequisites

- **Python 3.10+**
- **Ollama** installed and running
- **API Keys** for Reddit and YouTube (optional)

### 1. Install Ollama

```bash
# Download from https://ollama.ai/
# Then:
ollama pull mistral
```

### 2. Clone and Configure

```bash
git clone https://github.com/your-repo/SCRIBE.git
cd SCRIBE

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# or: source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Credentials

Create a `.env` file at the root:

```env
# Reddit (https://reddit.com/prefs/apps)
REDDIT_CLIENT_ID=your_id
REDDIT_CLIENT_SECRET=your_secret
REDDIT_USER_AGENT=SCRIBE/1.0

# YouTube (https://console.cloud.google.com/)
YOUTUBE_API_KEY=your_key

# Ollama
OLLAMA_HOST=http://localhost:11434

# Discord (optional)
DISCORD_WEBHOOK_URL=your_webhook
```

**Note**: Without Reddit/YouTube credentials, the app will still work but without those sources.

---

## Usage

### Run a Collection

```bash
python main.py --mode once
```

The report will be generated in `data/reports/`.

### View Statistics

```bash
python main.py --mode stats
```

Shows: processed content, relevance rate, breakdown by source/category.

### Change Report Language

```bash
python main.py --mode once --lang en  # English
python main.py --mode once --lang fr  # French (default)
```

---

## Configuration

### Sources (config/settings.yaml)

```yaml
reddit:
  subreddits:
    - MachineLearning
    - LocalLLaMA
    - OpenAI
    # Add your subreddits...
  posts_limit: 5
  timeframe: "day"

youtube:
  keywords:
    - "AI research"
  channels:
    - "@YannicKilcher"
    - "@AIExplained-"
  languages: ["en", "fr"]
```

### AI Model (config/ollama_config.yaml)

```yaml
model: "mistral"  # or phi4, llama3, qwen2.5...

parameters:
  temperature: 0.3
  num_ctx: 32768
```

### Relevance Threshold

```yaml
analysis:
  relevance_threshold: 7  # Keep only score >= 7/10
```

### Discord Notifications

```yaml
discord:
  enabled: true
  send_metrics: true
  mention_role: "@everyone"  # or "" to disable
```

## Generated Report Example

# SCRIBE - AI INTELLIGENCE REPORT
## 2025-01-15 | 08:00

AI continues to advance rapidly with major breakthroughs
in LLM reasoning and multimodal architectures...

## Large Language Models
   3 insight(s)

### 1. GPT-5 Released with Enhanced Reasoning
**Source**: Reddit
**Link**: https://reddit.com/r/OpenAI/...
**Relevance**: 9/10
**Author**: u/ai_researcher
**Date**: 2025-01-14

**Insights**: OpenAI launched GPT-5 with significant improvements
in logical reasoning and contextual understanding...

---

## Robotics
   1 insight(s)

### 1. Tesla Optimus Gen 3 Demo
**Source**: YouTube
**Link**: https://youtube.com/watch?v=...
**Relevance**: 8/10

**Insights**: New demonstration of Tesla's humanoid robot...

---

*Report generated by SCRIBE - 4 total insights*
```

---

## Analysis Categories

SCRIBE automatically classifies content into 22 categories:

- Large Language Models
- AI Ethics & Safety
- Computer Vision
- Robotics
- AI Agents & Autonomous Systems
- Generative AI
- AI Hardware & Infrastructure
- Open Source Models
- AI in Healthcare
- AI Regulation & Policy
- ... and more

---

## Troubleshooting

### "Model not found"

```bash
ollama list              # View installed models
ollama pull mistral      # Install missing model
```

### "Reddit credentials invalid"

Check that your `.env` contains the correct values from https://reddit.com/prefs/apps

### "YouTube quota exceeded"

YouTube API has a free daily limit. Reduce `videos_limit` in `config/settings.yaml`.

### Ollama too slow

- Reduce `batch_size` in `config/ollama_config.yaml`
- Or use a lighter model (phi4 vs llama3)

### Not enough insights

- Lower `relevance_threshold` (e.g., 5 instead of 7)
- Increase `posts_limit` or `videos_limit`
- Add more subreddits/channels

---

## Logs

- **Application**: `logs/scribe.log`
- **Raw data**: `data/raw_logs/` (for debugging)

For more details:

```python
# In src/utils.py
logging.basicConfig(level=logging.DEBUG)  # Instead of INFO
```

---

## Roadmap

- [x] Reddit and YouTube collection
- [x] Local AI analysis (Ollama)
- [x] Semantic deduplication
- [x] Markdown reports
- [x] Discord notifications
- [ ] Emerging trend detection

---

## Contributing

The project is designed to be extensible:

- Add sources: `src/collectors/`
- New processors: `src/processors/`
- Report templates: `src/storage/report_generator.py`

---

## License

MIT License - Free to use and modify

---

<div align="center">
  <b>SCRIBE - Your Automated AI Intelligence Assistant</b>
</div>
