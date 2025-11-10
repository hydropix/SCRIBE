<div align="center">
  <img src="SCRIBE_Logo.png" alt="SCRIBE Logo" width="200"/>
</div>

# SCRIBE - Source Content Retrieval and Intelligence Bot Engine

Automated intelligence gathering system that collects, analyzes, and synthesizes the latest AI news from Reddit and YouTube, using Ollama (Mistral, Phi4, etc.) for analysis and Markdown report generation.

## Features

- **Multi-source collection**: Reddit (specialized subreddits) and YouTube (video transcripts)
- **Local LLM analysis**: Uses Ollama with your RTX4090 GPU to filter and analyze content
- **Intelligent deduplication**: Semantic detection of redundant content
- **Markdown reports**: Daily generation of structured and professional reports
- **Flexible configuration**: Easy model switching, context size, sources
- **SQLite cache**: Avoids reprocessing already analyzed content
- **Integrated scheduler**: Automatic daily execution

## Architecture

```
SCRIBE/
├── config/
│   ├── settings.yaml          # Source and criteria configuration
│   └── ollama_config.yaml     # Ollama configuration (model, prompts)
├── src/
│   ├── collectors/
│   │   ├── reddit_collector.py    # Reddit collection via PRAW
│   │   └── youtube_collector.py   # YouTube collection with transcripts
│   ├── processors/
│   │   ├── ollama_client.py       # Ollama client
│   │   ├── content_analyzer.py    # Relevance analysis
│   │   └── deduplicator.py        # Semantic deduplication
│   ├── storage/
│   │   ├── cache_manager.py       # SQLite cache management
│   │   └── report_generator.py    # Markdown report generation
│   ├── scheduler.py               # Daily scheduling
│   └── utils.py                   # Utilities
├── data/
│   ├── cache.db                   # SQLite cache
│   └── reports/                   # Generated reports
├── logs/                          # Application logs
├── main.py                        # Entry point
└── requirements.txt
```

## Prerequisites

### 1. Python 3.10+

```bash
python --version
```

### 2. Ollama installed and running

```bash
# Install Ollama: https://ollama.ai/

# Start Ollama server
ollama serve

# Download a model (Mistral recommended for RTX4090)
ollama pull mistral

# Or Phi4 (lighter)
ollama pull phi4
```

### 3. API Credentials

#### Reddit API

1. Go to https://www.reddit.com/prefs/apps
2. Create an application (type: "script")
3. Note the `client_id` and `client_secret`

#### YouTube API

1. Go to https://console.cloud.google.com/
2. Create a project
3. Enable "YouTube Data API v3"
4. Create an API key in "Credentials"

## Installation

### 1. Clone the repository

```bash
cd SCRIBE
```

### 2. Create a virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure credentials

```bash
# Copy the template
copy .env.example .env

# Edit .env with your credentials
notepad .env
```

Fill with your actual values:

```env
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
REDDIT_USER_AGENT=SCRIBE/1.0

YOUTUBE_API_KEY=your_api_key

OLLAMA_HOST=http://localhost:11434
```

## Configuration

### Customize sources (config/settings.yaml)

```yaml
reddit:
  subreddits:
    - MachineLearning
    - artificial
    - LocalLLaMA
    # Add your subreddits...

youtube:
  keywords:
    - "AI news"
    - "LLM tutorial"
  channels:
    - "@TwoMinutePapers"
    # Add your channels...
```

### Change Ollama model (config/ollama_config.yaml)

```yaml
# Easily switch models
model: "mistral"  # or "phi4", "llama3", "qwen2.5"...

parameters:
  num_ctx: 32768  # Context size
  temperature: 0.3
```

## Usage

### Mode 1: Single execution (test)

```bash
python main.py --mode once
```

Executes a complete intelligence cycle immediately.

### Mode 2: Daily scheduling

```bash
# Start scheduler (runs daily at 08:00)
python main.py --mode schedule

# With immediate execution then scheduling
python main.py --mode schedule --run-now
```

Modify the time in `config/settings.yaml`:

```yaml
scheduler:
  run_time: "08:00"  # 24h format
  timezone: "Europe/Paris"
```

### Mode 3: Statistics

```bash
python main.py --mode stats
```

Displays cache statistics (processed content, relevance rate, etc.).

## Execution Workflow

When you run the intelligence gathering, here's what happens:

1. **Collection**: Retrieval of recent Reddit posts and YouTube videos
2. **Cache filtering**: Exclusion of already processed content
3. **LLM analysis**: Ollama analyzes each content to:
   - Determine relevance (score /10)
   - Assign a category
   - Extract key insights
4. **Deduplication**: Elimination of redundant content
5. **Report generation**: Creation of a Markdown file in `data/reports/`

## Report Examples

Generated reports look like:

```markdown
# AI Intelligence Report - 2025-01-15

## 📊 Executive Summary

This week, major trends include improvements in LLM reasoning
capabilities and new vision-language architectures...

## 📈 Metrics

- Total analyzed: 150
- Relevant: 23 (15.3%)
- Average score: 6.2/10

## Large Language Models

### 1. GPT-5 Released with Enhanced Reasoning

**Source**: Reddit
**Link**: https://reddit.com/...
**Relevance**: 9/10

**Insights**:
OpenAI launched GPT-5 with significant improvements...
```

## Advanced Customization

### Modify system prompts

Edit `config/ollama_config.yaml` to adjust instructions given to Ollama:

```yaml
prompts:
  relevance_analyzer: |
    You are an AI expert. Analyze the content and determine
    its relevance for technology intelligence...
```

### Adjust relevance threshold

In `config/settings.yaml`:

```yaml
analysis:
  relevance_threshold: 7  # Only content >= 7/10
```

### Modify categories

```yaml
analysis:
  categories:
    - "Large Language Models"
    - "Computer Vision"
    - "Robotics"  # Add new categories
```

## RTX4090 Optimization

Your GPU can handle large models. Recommendations:

- **Mistral (7B)**: Excellent speed/quality balance
- **Phi4 (14B)**: More compact, very performant
- **Llama3 (70B quantized)**: Maximum quality if you have time

Adjust `num_ctx` according to your needs:

```yaml
parameters:
  num_ctx: 32768  # Mistral supports 32K
  # or 128000 for Llama3 with very long contexts
```

## Troubleshooting

### Error "Model not found"

```bash
# Check installed models
ollama list

# Install missing model
ollama pull mistral
```

### Error "Reddit credentials invalid"

Verify that your `.env` contains the correct values from https://www.reddit.com/prefs/apps

### Error "YouTube quota exceeded"

YouTube API has a daily free limit (10,000 units). Reduce `videos_limit` in `config/settings.yaml`.

### Ollama too slow

Reduce batch size in `config/ollama_config.yaml`:

```yaml
performance:
  batch_size: 3  # Instead of 5
```

## Logging

Logs are saved in `logs/scribe.log`.

For more details, modify the log level in `src/utils.py`:

```python
logging.basicConfig(level=logging.DEBUG)  # Instead of INFO
```

## Unit Tests

Each module can be tested individually:

```bash
# Test Reddit collector
python src/collectors/reddit_collector.py

# Test analyzer
python src/processors/content_analyzer.py

# Test Ollama
python src/processors/ollama_client.py
```

## Contributing

This project is designed to be easily extensible:

- Add new sources in `src/collectors/`
- Create new analysis processors in `src/processors/`
- Modify report templates in `src/storage/report_generator.py`

## Roadmap

- [ ] Support for additional sources (HackerNews, ArXiv)
- [ ] Notifications (email, Discord, Slack)
- [ ] Interactive web dashboard
- [ ] PDF export of reports
- [ ] Sentiment analysis
- [ ] Emerging trend detection

## License

MIT License - Free to use and modify

## Support

For questions or bugs, open an issue on GitHub.

---

**Developed with Mistral/Phi4 on RTX4090** 🚀
