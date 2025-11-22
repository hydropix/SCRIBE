# Fallback Mechanism for Failed Notifications

## Overview

SCRIBE includes an intelligent **fallback retry mechanism** that handles notification failures gracefully. When sending notifications to Discord or Synology Chat fails, the system automatically retries using the **persisted Markdown report** as the data source.

## How It Works

### Normal Flow
1. Collect data from Reddit/YouTube
2. Analyze with Ollama
3. Generate Markdown report
4. Send notifications (Discord/Synology)

### Fallback Flow (when notification fails)
1. **Detect failure** - Send method returns `False` or raises exception
2. **Parse report** - Extract content items from the already-generated Markdown file
3. **Reconstruct data** - Rebuild the `relevant_contents` structure from parsed data
4. **Retry sending** - Attempt to send again with exponential backoff
5. **Multiple attempts** - Up to 3 retries (configurable)

## Key Benefits

✅ **No re-collection** - Doesn't fetch data from Reddit/YouTube again
✅ **No re-analysis** - Doesn't call Ollama again
✅ **Fast recovery** - Uses cached report file as source of truth
✅ **Automatic retry** - Handles transient network issues
✅ **Exponential backoff** - Delays increase: 5s, 10s, 20s (configurable)

## Architecture

### Components

**FallbackManager** ([src/notifiers/fallback_manager.py](../src/notifiers/fallback_manager.py))
- Parses Markdown reports to extract content items
- Manages retry logic with exponential backoff
- Reconstructs data structures compatible with notifiers

**Report Generator** ([src/storage/report_generator.py](../src/storage/report_generator.py))
- Embeds hidden metadata in HTML comments for easier parsing
- Includes: `source`, `video_id`, `image_url`, `subreddit`
- Example: `<!-- source=reddit | video_id=abc123 -->`

**Main Orchestrator** ([main.py](../main.py))
- Captures send failures (Step 7 & 7b)
- Triggers fallback automatically
- Logs all retry attempts

## Configuration

Add to your package's `settings.yaml`:

```yaml
fallback:
  max_retries: 3      # Number of retry attempts
  retry_delay: 5.0    # Initial delay in seconds (exponential backoff applied)
```

**Default values:**
- `max_retries`: 3
- `retry_delay`: 5.0

**Retry delays (exponential backoff):**
- Attempt 1: immediate (no delay)
- Attempt 2: 5 seconds
- Attempt 3: 10 seconds
- Attempt 4: 20 seconds

## Report Format

The Markdown report includes:

### Visible Metadata
```markdown
📎 **Metadata**
  - [Source](https://reddit.com/...)
  - Relevance: 8/10
  - Author: username
  - Date: 2025-11-22
```

### Hidden Metadata (HTML comments)
```markdown
<!-- source=reddit | image_url=https://... | subreddit=MachineLearning -->
```

This hidden metadata ensures the fallback parser can accurately reconstruct:
- Discord rich embeds with images
- YouTube thumbnails
- Source attribution

## Usage Example

### Automatic Fallback

The fallback mechanism is **completely automatic**. You don't need to do anything special:

```python
# In main.py - automatically handled
success = discord_notifier.send_rich_report(
    relevant_contents=unique,
    mention_role=""
)

# If send fails, fallback triggers automatically
if not success:
    # Fallback manager parses the report and retries
    success = fallback_manager.retry_with_fallback(
        notifier=discord_notifier,
        send_method='send_rich_report',
        report_path=report_result['path']
    )
```

### Manual Testing

Test the parser directly:

```bash
python tests/test_fallback.py
```

Test individual components:

```python
from src.notifiers.fallback_manager import FallbackManager

manager = FallbackManager("ai_trends")

# Find latest report
report_path = manager.find_latest_report()

# Parse it
items = manager.parse_report(report_path)

# Check results
print(f"Parsed {len(items)} items")
for item in items:
    print(f"- {item['title']}")
    print(f"  Category: {item['category']}")
    print(f"  Metadata: {item['metadata'].keys()}")
```

## Logs

Fallback activity is logged with clear messages:

```
[INFO] STEP 7: Sending Discord notification...
[WARNING] Discord notification failed, attempting fallback...
[INFO] Attempting fallback retry for send_rich_report...
[INFO] Retry attempt 1/3
[INFO] Parsing report: data/ai_trends/reports/ai_trends_report_2025-11-22.md
[INFO] Successfully parsed 18 items from report
[INFO] Waiting 5.0s before retry...
[INFO] Fallback retry succeeded on attempt 1
[INFO] Discord notification sent successfully via fallback
```

## Error Handling

### When Fallback Succeeds
```
✓ Discord notification sent successfully via fallback
```

### When All Retries Fail
```
✗ Discord notification failed even after fallback retries
```

### When Report Parse Fails
```
✗ Failed to parse report for fallback
```

## Supported Notifiers

- ✅ **Discord** - Both `send_rich_report` (embeds) and `send_full_report` (text)
- ✅ **Synology Chat** - `send_rich_report` (formatted messages)

## Limitations

1. **Summary notifications** - Currently, summaries are not retried with fallback (they require Ollama to generate)
2. **Real-time data** - Fallback uses persisted report, so very recent updates might not be included
3. **Parse accuracy** - Requires well-formed Markdown (automatically generated reports are always valid)

## Future Enhancements

Potential improvements:

- [ ] Cache Ollama-generated summaries for fallback retry
- [ ] Support manual trigger of fallback via CLI command
- [ ] Add webhook health checks before sending
- [ ] Persistent retry queue for offline scenarios

## Troubleshooting

### "No reports found"
**Cause:** Package hasn't generated any reports yet
**Solution:** Run `python main.py --package ai_trends --mode once` first

### "Failed to parse report"
**Cause:** Report format is malformed or corrupted
**Solution:** Check report file manually, regenerate if needed

### "All retry attempts failed"
**Cause:** Persistent webhook issues (invalid URL, network down)
**Solution:**
1. Verify webhook URL in `.env`
2. Test webhook manually with `curl`
3. Check network connectivity
4. Review Discord/Synology rate limits

## Testing

Run the test suite:

```bash
# Test fallback parsing
python tests/test_fallback.py

# Expected output:
# ✓ PASSED: Parse Report
# ✓ PASSED: Fallback Simulation
# Results: 2/2 tests passed
```

## Related Documentation

- [Discord Forum Channels](discord_forum_channels.md) - Forum channel setup
- [CLAUDE.md](../CLAUDE.md) - Complete project documentation
- [Package Configuration](../packages/ai_trends/settings.yaml) - Example config
