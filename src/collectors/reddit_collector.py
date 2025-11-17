"""Reddit data collector via PRAW"""

import os
import logging
from typing import List, Dict, Any
from datetime import datetime, timedelta
import praw
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.utils import load_config


class RedditCollector:
    """Collects Reddit posts and comments about AI"""

    def __init__(
        self,
        settings_path: str = "config/settings.yaml",
        client_id: str = None,
        client_secret: str = None,
        user_agent: str = None
    ):
        """
        Initializes the Reddit collector

        Args:
            settings_path: Path to configuration file
            client_id: Reddit Client ID (or from .env)
            client_secret: Reddit Client secret (or from .env)
            user_agent: User agent (or from .env)
        """
        self.logger = logging.getLogger("SCRIBE.RedditCollector")
        self.config = load_config(settings_path)
        self.reddit_config = self.config.get('reddit', {})

        # Credentials from env or parameters
        self.client_id = client_id or os.getenv('REDDIT_CLIENT_ID')
        self.client_secret = client_secret or os.getenv('REDDIT_CLIENT_SECRET')
        self.user_agent = user_agent or os.getenv('REDDIT_USER_AGENT', 'VeilleAuto/1.0')

        if not self.client_id or not self.client_secret:
            raise ValueError(
                "Reddit credentials not found. "
                "Please set REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET in .env"
            )

        # Initialize PRAW
        self.reddit = praw.Reddit(
            client_id=self.client_id,
            client_secret=self.client_secret,
            user_agent=self.user_agent
        )

        self.reddit.read_only = True
        self.logger.info("Reddit collector initialized")

    def collect_posts(
        self,
        subreddits: List[str] = None,
        limit: int = None,
        timeframe: str = None,
        include_comments: bool = None,
        comments_limit: int = None
    ) -> List[Dict[str, Any]]:
        """
        Collects posts from configured subreddits

        Args:
            subreddits: List of subreddits (or from config)
            limit: Number of posts per subreddit (or from config)
            timeframe: Period (day, week, month, year, all)
            include_comments: Include comments
            comments_limit: Number of comments per post

        Returns:
            List of dictionaries containing post data
        """
        # Use config values if not provided
        subreddits = subreddits or self.reddit_config.get('subreddits', [])
        limit = limit or self.reddit_config.get('posts_limit', 50)
        timeframe = timeframe or self.reddit_config.get('timeframe', 'day')
        include_comments = include_comments if include_comments is not None else self.reddit_config.get('include_comments', True)
        comments_limit = comments_limit or self.reddit_config.get('comments_limit', 10)

        all_posts = []

        for subreddit_name in subreddits:
            try:
                self.logger.info(f"Collecting from r/{subreddit_name}...")

                subreddit = self.reddit.subreddit(subreddit_name)

                # Retrieve top posts for the period
                posts = subreddit.top(time_filter=timeframe, limit=limit)

                for post in posts:
                    post_data = self._extract_post_data(post)

                    # Add comments if requested
                    if include_comments:
                        post_data['comments'] = self._extract_comments(post, comments_limit)

                    all_posts.append(post_data)

                self.logger.info(f"Collected {len([p for p in all_posts if p['subreddit'] == subreddit_name])} posts from r/{subreddit_name}")

            except Exception as e:
                self.logger.error(f"Error collecting from r/{subreddit_name}: {e}")

        self.logger.info(f"Total posts collected: {len(all_posts)}")
        return all_posts

    def _extract_post_data(self, post) -> Dict[str, Any]:
        """Extracts relevant data from a Reddit post"""

        # Extract image URL if present
        image_url = self._extract_image_url(post)

        return {
            'id': post.id,
            'title': post.title,
            'selftext': post.selftext,
            'url': post.url,
            'permalink': f"https://reddit.com{post.permalink}",
            'author': str(post.author) if post.author else '[deleted]',
            'subreddit': post.subreddit.display_name,
            'score': post.score,
            'upvote_ratio': post.upvote_ratio,
            'num_comments': post.num_comments,
            'created_utc': datetime.fromtimestamp(post.created_utc),
            'is_self': post.is_self,
            'link_flair_text': post.link_flair_text,
            'source': 'reddit',
            'image_url': image_url,  # New field for image
            'comments': []  # Will be filled if needed
        }

    def _extract_image_url(self, post) -> str:
        """
        Extracts image URL from a Reddit post if available

        Args:
            post: PRAW post object

        Returns:
            Image URL string or None if no image found
        """
        try:
            # Check if post URL is a direct image link
            if post.url and any(post.url.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
                return post.url

            # Check for Reddit-hosted images (i.redd.it)
            if post.url and 'i.redd.it' in post.url:
                return post.url

            # Check for imgur direct links
            if post.url and 'imgur.com' in post.url:
                # Convert imgur page to direct image if needed
                if not any(post.url.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
                    # Try to get direct link by adding .jpg
                    if '/a/' not in post.url and '/gallery/' not in post.url:
                        return post.url + '.jpg'
                return post.url

            # Check for Reddit preview images
            if hasattr(post, 'preview') and post.preview:
                images = post.preview.get('images', [])
                if images:
                    # Get the source (highest quality) image
                    source = images[0].get('source', {})
                    if source.get('url'):
                        # Reddit encodes URLs, need to decode
                        return source['url'].replace('&amp;', '&')

            # Check for Reddit gallery (multiple images) - get first image
            if hasattr(post, 'is_gallery') and post.is_gallery:
                if hasattr(post, 'media_metadata') and post.media_metadata:
                    # Get first image from gallery
                    for media_id in post.media_metadata:
                        media = post.media_metadata[media_id]
                        if media.get('e') == 'Image':
                            # Get the source image
                            if 's' in media and 'u' in media['s']:
                                return media['s']['u'].replace('&amp;', '&')
                            elif 'p' in media and media['p']:
                                # Fallback to preview
                                return media['p'][-1]['u'].replace('&amp;', '&')

            # Check post thumbnail as last resort (if it's a valid image)
            if hasattr(post, 'thumbnail') and post.thumbnail:
                if post.thumbnail.startswith('http') and post.thumbnail not in ['self', 'default', 'nsfw', 'spoiler']:
                    # Thumbnail is usually low quality, prefer preview
                    pass

        except Exception as e:
            self.logger.debug(f"Could not extract image from post {post.id}: {e}")

        return None

    def _extract_comments(self, post, limit: int) -> List[Dict[str, Any]]:
        """Extracts top comments from a post"""

        comments_data = []

        try:
            # Retrieve top comments
            post.comment_sort = 'top'
            post.comments.replace_more(limit=0)  # Avoid "load more comments"

            for comment in post.comments[:limit]:
                if hasattr(comment, 'body'):  # Verify it's a comment
                    comments_data.append({
                        'id': comment.id,
                        'body': comment.body,
                        'author': str(comment.author) if comment.author else '[deleted]',
                        'score': comment.score,
                        'created_utc': datetime.fromtimestamp(comment.created_utc)
                    })

        except Exception as e:
            self.logger.warning(f"Error extracting comments for post {post.id}: {e}")

        return comments_data

    def get_post_full_text(self, post_data: Dict[str, Any]) -> str:
        """
        Reconstructs the full text of a post for analysis

        Args:
            post_data: Post data

        Returns:
            Full text of post + comments
        """
        parts = [
            f"Titre: {post_data['title']}",
        ]

        if post_data['selftext']:
            parts.append(f"\nContenu:\n{post_data['selftext']}")

        if post_data['link_flair_text']:
            parts.append(f"\nFlair: {post_data['link_flair_text']}")

        # Add top comments
        if post_data.get('comments'):
            parts.append("\n--- Top Commentaires ---")
            for i, comment in enumerate(post_data['comments'][:5], 1):
                parts.append(f"\n[Comment {i} - Score: {comment['score']}]")
                parts.append(comment['body'][:500])  # Limit length

        return "\n".join(parts)

    def filter_by_date(
        self,
        posts: List[Dict[str, Any]],
        days_back: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Filters posts by date

        Args:
            posts: List of posts
            days_back: Number of days to go back

        Returns:
            Filtered posts
        """
        cutoff_date = datetime.now() - timedelta(days=days_back)

        filtered = [
            post for post in posts
            if post['created_utc'] >= cutoff_date
        ]

        self.logger.info(f"Filtered {len(filtered)}/{len(posts)} posts from last {days_back} day(s)")
        return filtered


if __name__ == "__main__":
    # Quick test
    import sys
    sys.path.append(str(Path(__file__).parent.parent.parent))

    from src.utils import load_env_variables, setup_logging

    setup_logging()
    load_env_variables()

    collector = RedditCollector()

    # Test with single subreddit
    posts = collector.collect_posts(
        subreddits=['MachineLearning'],
        limit=5,
        timeframe='week',
        include_comments=True,
        comments_limit=3
    )

    print(f"\n{len(posts)} posts collected")

    if posts:
        print("\nFirst post:")
        post = posts[0]
        print(f"Title: {post['title']}")
        print(f"Score: {post['score']}")
        print(f"Comments: {len(post['comments'])}")
        print(f"\nFull text (excerpt):")
        print(collector.get_post_full_text(post)[:500])
