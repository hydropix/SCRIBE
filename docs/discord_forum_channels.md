# Discord Forum Channels Support

## Overview

SCRIBE now supports Discord **forum channels** in addition to regular text channels. Forum channels require special webhook parameters to function correctly.

## Key Difference: Text Channels vs Forum Channels

### Text Channels (Regular)
- ✅ Work with standard webhook messages
- ✅ No special parameters required
- Messages appear directly in the channel

### Forum Channels
- ❌ Require `thread_name` parameter
- ✅ Each webhook message creates a new forum thread
- Without `thread_name`, Discord returns error:
  ```
  "Webhooks posted to forum channels must have a thread_name or thread_id"
  ```

## Configuration

Add the `thread_name` parameter to your Discord configuration in `packages/<package>/settings.yaml`:

```yaml
discord:
  enabled: true
  rich_embeds: true
  webhook_env: "DISCORD_AI_TRENDS_WEBHOOK"

  # For forum channels: specify thread_name
  thread_name: "AI Trends Report"

  summary:
    enabled: true
    webhook_env: "DISCORD_AI_TRENDS_SUMMARY_WEBHOOK"
    thread_name: "AI Daily Summary"
```

## Dynamic Thread Names

You can use dynamic values in your configuration, but the thread name will be static from the YAML. For time-based thread names, you can:

1. **Option 1: Use a generic name**
   ```yaml
   thread_name: "AI Trends Report"
   ```

2. **Option 2: Modify the code to generate dynamic names**
   The `DiscordNotifier` class supports `thread_name` in its config. You can override it programmatically:

   ```python
   from datetime import datetime

   # Override thread_name with current date
   config['thread_name'] = f"AI Trends - {datetime.now().strftime('%d %B %Y')}"
   notifier = DiscordNotifier(config)
   ```

## How It Works

When `thread_name` is configured, the Discord notifier automatically adds it to all webhook payloads:

```python
# Internal implementation
payload = {
    "content": "Your message",
    "thread_name": "AI Trends Report"  # Automatically added
}
```

This works for:
- ✅ Simple text messages
- ✅ Rich embeds
- ✅ Multiple embeds
- ✅ Message chunks (long reports)
- ✅ Summary notifications

## Testing

Use the provided test scripts to verify your forum webhook:

```bash
# Basic webhook test
python tests/test_discord_forum.py

# Integration test with SCRIBE notifier
python tests/test_discord_forum_integration.py
```

## Example: Full Configuration

```yaml
# packages/ai_trends/settings.yaml

discord:
  enabled: true
  rich_embeds: true
  send_executive_summary: true
  send_metrics: true
  mention_role: ""  # Optional: "@everyone" or role ID
  webhook_env: "DISCORD_AI_TRENDS_WEBHOOK"

  # Forum channel support
  thread_name: "🤖 AI Trends Report"

  summary:
    enabled: true
    webhook_env: "DISCORD_AI_TRENDS_SUMMARY_WEBHOOK"
    mention_role: ""

    # Separate thread name for summaries
    thread_name: "📊 Daily AI Summary"
```

## Environment Variables

Make sure your `.env` file contains the forum channel webhooks:

```bash
# Main report webhook (forum channel)
DISCORD_AI_TRENDS_WEBHOOK=https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_TOKEN

# Summary webhook (can be same or different forum)
DISCORD_AI_TRENDS_SUMMARY_WEBHOOK=https://discord.com/api/webhooks/YOUR_SUMMARY_WEBHOOK_ID/YOUR_TOKEN
```

## Creating a Forum Channel Webhook

1. Go to your Discord server
2. Create or select a **Forum Channel**
3. Right-click → **Edit Channel** → **Integrations** → **Webhooks**
4. **Create Webhook**
5. Copy the webhook URL
6. Add it to your `.env` file

## Troubleshooting

### Error: "Webhooks posted to forum channels must have a thread_name or thread_id"

**Solution:** Add `thread_name` to your Discord configuration in `settings.yaml`:

```yaml
discord:
  thread_name: "Your Thread Name"
```

### Messages work in text channels but not forum channels

**Cause:** Forum channels require the `thread_name` parameter.

**Solution:** Add the `thread_name` parameter as shown above.

### Want to use the same webhook for both text and forum channels?

**Not recommended.** Discord treats them differently:
- Text channels: reject `thread_name` parameter
- Forum channels: require `thread_name` parameter

Use separate webhooks for text and forum channels.

## Backwards Compatibility

If `thread_name` is **not** configured:
- ✅ Works perfectly with **text channels** (default behavior)
- ❌ Fails with **forum channels** (Discord error)

The implementation is backwards compatible - existing text channel configurations work without changes.
