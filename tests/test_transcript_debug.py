"""Debug transcript retrieval"""
from pathlib import Path
import sys

sys.path.append(str(Path.cwd()))

from src.utils import load_env_variables, setup_logging
from src.collectors.youtube_collector import YouTubeCollector
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound

setup_logging()
load_env_variables()

collector = YouTubeCollector()

# Collect videos without transcripts first
print(f'\n=== COLLECTING VIDEOS (without transcript filtering) ===')
videos = collector._search_by_keyword("AI research", max_results=5, days_back=7)

print(f'\nFound {len(videos)} videos')

# Test transcripts manually
for i, video in enumerate(videos[:3], 1):
    video_id = video['video_id']
    print(f'\n--- Video {i} ---')
    print(f'Title: {video["title"]}')
    print(f'Channel: {video["channel_title"]}')
    print(f'Video ID: {video_id}')
    print(f'URL: {video["url"]}')

    # Try to get transcript list
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

        print(f'\nAvailable transcripts:')
        for transcript in transcript_list:
            print(f'  - {transcript.language} ({transcript.language_code}) - Generated: {transcript.is_generated}')

        # Try to get transcript in fr/en
        try:
            transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['fr', 'en'])
            print(f'\nTranscript retrieved successfully!')
            print(f'Length: {len(transcript)} segments')
            text = " ".join([entry['text'] for entry in transcript])
            print(f'Total text length: {len(text)} characters')
            print(f'Preview: {text[:200]}...')
        except (TranscriptsDisabled, NoTranscriptFound) as e:
            print(f'\nNo transcript available in fr/en: {e}')

    except TranscriptsDisabled:
        print(f'\nTranscripts are disabled for this video')
    except NoTranscriptFound:
        print(f'\nNo transcripts found for this video')
    except Exception as e:
        print(f'\nError: {e}')
