"""Test with a single specific video"""
from pathlib import Path
import sys
import time

sys.path.append(str(Path.cwd()))

from src.utils import load_env_variables, setup_logging
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound

setup_logging()
load_env_variables()

# Test with a known video that has transcripts
test_videos = [
    ("vrTrOCQZoQE", "Computerphile - AI Slop"),
    ("_WJr8HvrYHY", "NotebookLM Deep Research"),
]

print("Waiting 30 seconds to avoid rate limiting...")
time.sleep(30)

for video_id, title in test_videos:
    print(f"\n=== Testing: {title} ===")
    print(f"Video ID: {video_id}")

    try:
        # List available transcripts
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

        print("Available transcripts:")
        for t in transcript_list:
            print(f"  - {t.language} ({t.language_code}) - Generated: {t.is_generated}")

        # Try to get transcript
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['en', 'fr'])
        text = " ".join([entry['text'] for entry in transcript])

        print(f"\n✅ SUCCESS!")
        print(f"Transcript length: {len(text)} characters")
        print(f"Preview: {text[:150]}...")

    except (TranscriptsDisabled, NoTranscriptFound) as e:
        print(f"❌ No transcript: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")

    # Wait between videos
    time.sleep(3)
