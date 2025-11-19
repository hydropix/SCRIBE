"""Test YouTube collector"""
from pathlib import Path
import sys

sys.path.append(str(Path.cwd()))

from src.utils import load_env_variables, setup_logging
from src.collectors.youtube_collector import YouTubeCollector

setup_logging()
load_env_variables()

collector = YouTubeCollector()

print(f'\nConfiguration YouTube:')
print(f'Keywords: {collector.youtube_config.get("keywords")}')
print(f'Channels: {collector.youtube_config.get("channels")}')
print(f'Videos limit: {collector.youtube_config.get("videos_limit")}')
print(f'Days back: {collector.youtube_config.get("days_back")}')
print(f'Languages: {collector.youtube_config.get("languages")}')

print(f'\n=== COLLECTE EN COURS ===')
videos = collector.collect_videos()

print(f'\n=== RESULTATS ===')
print(f'Total videos avec transcripts: {len(videos)}')

for i, v in enumerate(videos, 1):
    print(f'\n{i}. {v["title"]}')
    print(f'   Channel: {v["channel_title"]}')
    print(f'   URL: {v["url"]}')
    print(f'   Published: {v["published_at"]}')
    has_transcript = v.get("transcript") is not None
    transcript_len = len(v.get("transcript", ""))
    print(f'   Transcript: {"OUI" if has_transcript else "NON"} ({transcript_len} chars)')
    if has_transcript:
        print(f'   Preview: {v["transcript"][:200]}...')
