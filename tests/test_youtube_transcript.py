"""Test YouTube transcript retrieval"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
from googleapiclient.discovery import build

load_dotenv()


def test_transcript_single_video(video_id: str, languages: list = None):
    """Test transcript retrieval for a single video"""

    if languages is None:
        languages = ['en', 'fr']

    print(f"\n{'='*60}")
    print(f"Testing video: {video_id}")
    print(f"URL: https://www.youtube.com/watch?v={video_id}")
    print(f"Languages: {languages}")
    print('='*60)

    try:
        # Initialize API (v1.x style)
        api = YouTubeTranscriptApi()

        # First, list available transcripts
        print("\n1. Listing available transcripts...")
        transcript_list = api.list(video_id)

        print(f"   Available transcripts:")
        for t in transcript_list:
            print(f"   - {t.language} ({t.language_code}) - Generated: {t.is_generated}")

        # Try to fetch transcript
        print(f"\n2. Fetching transcript in {languages}...")
        transcript = api.fetch(video_id, languages=languages)

        # Get text
        full_text = " ".join([entry.text for entry in transcript])

        print(f"\n3. SUCCESS! Transcript retrieved:")
        print(f"   - Segments: {len(transcript)}")
        print(f"   - Total characters: {len(full_text)}")
        print(f"\n   First 500 characters:")
        print(f"   {full_text[:500]}...")

        return True, full_text

    except TranscriptsDisabled:
        print("\n   ERROR: Transcripts are disabled for this video")
        return False, None

    except NoTranscriptFound:
        print(f"\n   ERROR: No transcript found in languages {languages}")
        return False, None

    except Exception as e:
        print(f"\n   ERROR: {type(e).__name__}: {e}")
        return False, None


def get_recent_videos_from_channel(channel_handle: str, max_results: int = 3):
    """Get recent videos from a YouTube channel using the API"""

    api_key = os.getenv('YOUTUBE_API_KEY')
    if not api_key:
        print("ERROR: YOUTUBE_API_KEY not found in .env")
        return []

    youtube = build('youtube', 'v3', developerKey=api_key)

    # First, find channel ID from handle
    print(f"\n1. Finding channel ID for {channel_handle}...")
    search_response = youtube.search().list(
        part='snippet',
        q=channel_handle,
        type='channel',
        maxResults=1
    ).execute()

    if not search_response.get('items'):
        print(f"   Channel not found: {channel_handle}")
        return []

    channel_id = search_response['items'][0]['snippet']['channelId']
    channel_name = search_response['items'][0]['snippet']['title']
    print(f"   Found: {channel_name} ({channel_id})")

    # Get recent videos
    print(f"\n2. Fetching {max_results} recent videos...")
    videos_response = youtube.search().list(
        part='snippet',
        channelId=channel_id,
        type='video',
        order='date',
        maxResults=max_results
    ).execute()

    videos = []
    for item in videos_response.get('items', []):
        video_id = item['id']['videoId']
        title = item['snippet']['title']
        videos.append((video_id, f"{channel_name}: {title[:50]}..."))
        print(f"   - {video_id}: {title[:60]}...")

    return videos


def main():
    print("YouTube Transcript API Test")
    print("="*60)

    # You can test with a specific video ID
    if len(sys.argv) > 1:
        video_id = sys.argv[1]
        test_videos = [(video_id, "User-provided video")]
    else:
        # Get real recent videos from AI Explained channel
        print("\nFetching real videos from @aiexplained-official...")
        test_videos = get_recent_videos_from_channel("@aiexplained-official", max_results=2)

        if not test_videos:
            print("Could not fetch videos from channel. Testing with known video.")
            test_videos = [("dQw4w9WgXcQ", "Fallback test video")]

    results = []

    for video_id, description in test_videos:
        print(f"\n\nTesting transcript: {description}")
        success, _ = test_transcript_single_video(video_id)
        results.append((video_id, description, success))

    # Summary
    print("\n\n" + "="*60)
    print("SUMMARY")
    print("="*60)

    for video_id, description, success in results:
        status = "[OK]" if success else "[FAIL]"
        print(f"{status} - {description[:50]} ({video_id})")

    successful = sum(1 for _, _, s in results if s)
    print(f"\nTotal: {successful}/{len(results)} successful")


def test_full_collector():
    """Test the full YouTubeCollector flow"""

    print("\n\n" + "="*60)
    print("TESTING FULL YOUTUBE COLLECTOR")
    print("="*60)

    from src.collectors.youtube_collector import YouTubeCollector
    from src.package_manager import PackageManager

    # Load package config
    pm = PackageManager()
    pkg = pm.load_package("ai_trends")

    print(f"\nPackage loaded: {pkg.name}")
    print(f"YouTube config: {pkg.settings.get('youtube', {})}")

    # Initialize collector
    collector = YouTubeCollector(config=pkg.settings)

    # Test with just one channel to avoid API limits
    print("\n\nCollecting videos from @aiexplained-official only...")
    videos = collector.collect_videos(
        keywords=[],  # No keywords
        channels=["@aiexplained-official"],  # Just one channel
        videos_limit=2,
        days_back=7,
        languages=['en', 'fr']
    )

    print(f"\n\nResults:")
    print(f"- Videos collected: {len(videos)}")

    for i, video in enumerate(videos):
        print(f"\n--- Video {i+1} ---")
        print(f"Title: {video['title']}")
        print(f"Channel: {video['channel_title']}")
        print(f"Video ID: {video['video_id']}")
        print(f"Has transcript: {video.get('transcript') is not None}")
        if video.get('transcript'):
            print(f"Transcript length: {len(video['transcript'])} chars")
            print(f"Transcript preview: {video['transcript'][:200]}...")

    return len(videos) > 0


if __name__ == "__main__":
    # Run basic transcript test
    main()

    # Run full collector test
    test_full_collector()
