"""Test updated YouTube collector with rate limiting"""
from pathlib import Path
import sys

sys.path.append(str(Path.cwd()))

from src.utils import load_env_variables, setup_logging
from src.collectors.youtube_collector import YouTubeCollector

setup_logging()
load_env_variables()

collector = YouTubeCollector()

print(f'\n=== TEST WITH RATE LIMITING ===')
print(f'Configuration:')
print(f'  - Keywords: {collector.youtube_config.get("keywords")}')
print(f'  - Videos limit: {collector.youtube_config.get("videos_limit")}')
print(f'  - Days back: {collector.youtube_config.get("days_back")}')
print(f'  - Languages: {collector.youtube_config.get("languages")}')

print(f'\n=== COLLECTING (with 2s delay between transcripts) ===')
videos = collector.collect_videos()

print(f'\n=== RESULTATS ===')
print(f'Total videos avec transcripts: {len(videos)}')

if videos:
    print(f'\n--- Vidéos collectées ---')
    for i, v in enumerate(videos[:5], 1):  # Show first 5
        print(f'\n{i}. {v["title"]}')
        print(f'   Channel: {v["channel_title"]}')
        print(f'   Source: {v["source_query"]}')
        print(f'   URL: {v["url"]}')
        transcript_len = len(v.get("transcript", ""))
        print(f'   Transcript: {transcript_len} chars')
        if transcript_len > 0:
            print(f'   Preview: {v["transcript"][:100]}...')
else:
    print('\nAucune vidéo avec transcript trouvée.')
    print('Possible causes:')
    print('  - Pas de vidéos publiées dans la période (days_back)')
    print('  - Pas de transcripts disponibles en fr/en')
    print('  - Rate limiting YouTube encore actif')
