"""Test YouTube collector with extended days_back"""
from pathlib import Path
import sys

sys.path.append(str(Path.cwd()))

from src.utils import load_env_variables, setup_logging
from src.collectors.youtube_collector import YouTubeCollector

setup_logging()
load_env_variables()

collector = YouTubeCollector()

print(f'\n=== TEST WITH 7 DAYS BACK ===')
videos = collector.collect_videos(days_back=7, videos_limit=2)

print(f'\n=== RESULTATS ===')
print(f'Total videos avec transcripts: {len(videos)}')

for i, v in enumerate(videos, 1):
    print(f'\n{i}. {v["title"]}')
    print(f'   Channel: {v["channel_title"]}')
    print(f'   URL: {v["url"]}')
    print(f'   Published: {v["published_at"]}')
    print(f'   Source query: {v["source_query"]}')
    has_transcript = v.get("transcript") is not None
    transcript_len = len(v.get("transcript", ""))
    print(f'   Transcript: {"OUI" if has_transcript else "NON"} ({transcript_len} chars)')
    if has_transcript:
        print(f'   Preview: {v["transcript"][:150]}...')
