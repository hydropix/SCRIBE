"""YouTube video collector with transcript extraction"""

import os
import logging
import time
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.utils import load_config


class YouTubeCollector:
    """Collects YouTube videos and their transcripts"""

    def __init__(
        self,
        settings_path: str = "config/settings.yaml",
        api_key: str = None
    ):
        """
        Initializes the YouTube collector

        Args:
            settings_path: Path to configuration file
            api_key: YouTube API key (or from .env)
        """
        self.logger = logging.getLogger("SCRIBE.YouTubeCollector")
        self.config = load_config(settings_path)
        self.youtube_config = self.config.get('youtube', {})

        # API Key from env or parameters
        self.api_key = api_key or os.getenv('YOUTUBE_API_KEY')

        if not self.api_key:
            raise ValueError(
                "YouTube API key not found. "
                "Please set YOUTUBE_API_KEY in .env"
            )

        # Initialize YouTube API client
        self.youtube = build('youtube', 'v3', developerKey=self.api_key)

        self.logger.info("YouTube collector initialized")

    def collect_videos(
        self,
        keywords: List[str] = None,
        channels: List[str] = None,
        videos_limit: int = None,
        days_back: int = None,
        languages: List[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Collects YouTube videos according to criteria

        Args:
            keywords: List of keywords to search
            channels: List of channels to monitor
            videos_limit: Number of videos per search
            days_back: Number of days to go back
            languages: Accepted languages for transcripts

        Returns:
            List of videos with metadata and transcripts
        """
        # Use config values if not provided
        keywords = keywords or self.youtube_config.get('keywords', [])
        channels = channels or self.youtube_config.get('channels', [])
        videos_limit = videos_limit or self.youtube_config.get('videos_limit', 20)
        days_back = days_back or self.youtube_config.get('days_back', 1)
        languages = languages or self.youtube_config.get('languages', ['en', 'fr'])

        all_videos = []

        # Collect by keywords
        for keyword in keywords:
            try:
                videos = self._search_by_keyword(keyword, videos_limit, days_back)
                all_videos.extend(videos)
                self.logger.info(f"Collected {len(videos)} videos for keyword: {keyword}")
            except Exception as e:
                self.logger.error(f"Error searching keyword '{keyword}': {e}")

        # Collect by channels
        for channel in channels:
            try:
                videos = self._search_by_channel(channel, videos_limit, days_back)
                all_videos.extend(videos)
                self.logger.info(f"Collected {len(videos)} videos from channel: {channel}")
            except Exception as e:
                self.logger.error(f"Error searching channel '{channel}': {e}")

        # Deduplicate by video_id
        unique_videos = {}
        for video in all_videos:
            if video['video_id'] not in unique_videos:
                unique_videos[video['video_id']] = video

        all_videos = list(unique_videos.values())

        # Enrich with transcripts
        all_videos = self._add_transcripts(all_videos, languages)

        self.logger.info(f"Total unique videos collected: {len(all_videos)}")
        return all_videos

    def _search_by_keyword(
        self,
        keyword: str,
        max_results: int,
        days_back: int
    ) -> List[Dict[str, Any]]:
        """Search by keyword"""

        # Calculate start date
        published_after = (datetime.now() - timedelta(days=days_back)).isoformat() + 'Z'

        try:
            request = self.youtube.search().list(
                part='snippet',
                q=keyword,
                type='video',
                order='relevance',
                maxResults=max_results,
                publishedAfter=published_after,
                relevanceLanguage='en'  # Prioritize English
            )

            response = request.execute()

            videos = []
            for item in response.get('items', []):
                video_data = self._extract_video_data(item, source_query=keyword)
                videos.append(video_data)

            return videos

        except Exception as e:
            self.logger.error(f"Error in YouTube API search for '{keyword}': {e}")
            return []

    def _search_by_channel(
        self,
        channel_identifier: str,
        max_results: int,
        days_back: int
    ) -> List[Dict[str, Any]]:
        """Search in a specific channel"""

        try:
            # If it's a handle (@username), we must first find the channel ID
            if channel_identifier.startswith('@'):
                channel_id = self._get_channel_id_from_handle(channel_identifier)
            else:
                channel_id = channel_identifier

            if not channel_id:
                self.logger.warning(f"Could not find channel ID for {channel_identifier}")
                return []

            # Calculate start date
            published_after = (datetime.now() - timedelta(days=days_back)).isoformat() + 'Z'

            # Search videos from the channel
            request = self.youtube.search().list(
                part='snippet',
                channelId=channel_id,
                type='video',
                order='date',
                maxResults=max_results,
                publishedAfter=published_after
            )

            response = request.execute()

            videos = []
            for item in response.get('items', []):
                video_data = self._extract_video_data(item, source_query=channel_identifier)
                videos.append(video_data)

            return videos

        except Exception as e:
            self.logger.error(f"Error searching channel '{channel_identifier}': {e}")
            return []

    def _get_channel_id_from_handle(self, handle: str) -> Optional[str]:
        """Retrieves channel ID from a handle (@username)"""

        try:
            # Search channel by handle
            request = self.youtube.search().list(
                part='snippet',
                q=handle,
                type='channel',
                maxResults=1
            )

            response = request.execute()

            if response.get('items'):
                return response['items'][0]['snippet']['channelId']

        except Exception as e:
            self.logger.error(f"Error getting channel ID for {handle}: {e}")

        return None

    def _extract_video_data(self, item: Dict, source_query: str = "") -> Dict[str, Any]:
        """Extracts data from a video"""

        snippet = item.get('snippet', {})
        video_id = item['id'].get('videoId') if isinstance(item['id'], dict) else item['id']

        return {
            'video_id': video_id,
            'title': snippet.get('title', ''),
            'description': snippet.get('description', ''),
            'channel_title': snippet.get('channelTitle', ''),
            'channel_id': snippet.get('channelId', ''),
            'published_at': snippet.get('publishedAt', ''),
            'thumbnail_url': snippet.get('thumbnails', {}).get('high', {}).get('url', ''),
            'url': f"https://www.youtube.com/watch?v={video_id}",
            'source_query': source_query,
            'source': 'youtube',
            'transcript': None  # Will be added later
        }

    def _add_transcripts(
        self,
        videos: List[Dict[str, Any]],
        languages: List[str]
    ) -> List[Dict[str, Any]]:
        """Adds transcripts to videos with rate limiting"""

        videos_with_transcripts = []

        for i, video in enumerate(videos):
            try:
                # Rate limiting: wait 3 seconds between transcript requests
                # to avoid YouTube 429 "Too Many Requests" errors
                # Conservative delay to ensure reliability
                if i > 0:
                    time.sleep(3)

                transcript = self._get_transcript(video['video_id'], languages)

                if transcript:
                    video['transcript'] = transcript
                    videos_with_transcripts.append(video)
                    self.logger.debug(f"Transcript found for: {video['title']}")
                else:
                    self.logger.debug(f"No transcript for: {video['title']}")

            except Exception as e:
                self.logger.warning(f"Error getting transcript for {video['video_id']}: {e}")

        self.logger.info(
            f"Transcripts found: {len(videos_with_transcripts)}/{len(videos)} videos"
        )

        return videos_with_transcripts

    def _get_transcript(
        self,
        video_id: str,
        languages: List[str]
    ) -> Optional[str]:
        """Retrieves the transcript of a video"""

        try:
            # Try to retrieve transcript in requested languages
            transcript_list = YouTubeTranscriptApi.get_transcript(
                video_id,
                languages=languages
            )

            # Concatenate text
            transcript_text = " ".join([entry['text'] for entry in transcript_list])

            return transcript_text

        except (TranscriptsDisabled, NoTranscriptFound):
            return None
        except Exception as e:
            self.logger.debug(f"Unexpected error getting transcript for {video_id}: {e}")
            return None

    def get_video_full_text(self, video_data: Dict[str, Any]) -> str:
        """
        Reconstructs the full text of a video for analysis

        Args:
            video_data: Video data

        Returns:
            Full text
        """
        parts = [
            f"Titre: {video_data['title']}",
            f"\nChaîne: {video_data['channel_title']}",
        ]

        if video_data.get('description'):
            parts.append(f"\nDescription:\n{video_data['description'][:500]}")

        if video_data.get('transcript'):
            parts.append(f"\n--- Transcript ---\n{video_data['transcript'][:3000]}")

        return "\n".join(parts)


if __name__ == "__main__":
    # Quick test
    import sys
    sys.path.append(str(Path(__file__).parent.parent.parent))

    from src.utils import load_env_variables, setup_logging

    setup_logging()
    load_env_variables()

    collector = YouTubeCollector()

    # Test with keyword
    videos = collector.collect_videos(
        keywords=['GPT-4'],
        channels=[],
        videos_limit=5,
        days_back=7
    )

    print(f"\n{len(videos)} videos collected with transcripts")

    if videos:
        print("\nFirst video:")
        video = videos[0]
        print(f"Title: {video['title']}")
        print(f"Channel: {video['channel_title']}")
        print(f"Transcript available: {video['transcript'] is not None}")
        if video['transcript']:
            print(f"Transcript length: {len(video['transcript'])} characters")
