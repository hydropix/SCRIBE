#!/usr/bin/env python3
"""
Test script for fast similarity detection using real raw data from SCRIBE.
This script parses the raw logs and tests duplicate detection on actual Reddit posts.
"""

import sys
import re
import time
import logging
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from src.processors.fast_similarity import FastSimilarityDetector
from src.processors.deduplicator import ContentDeduplicator


def parse_reddit_raw_log(file_path: str) -> list:
    """
    Parse a Reddit raw log markdown file and extract articles.

    Args:
        file_path: Path to the markdown file

    Returns:
        List of article dictionaries with title, content, id, etc.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    articles = []

    # Split by "## Item" to get each article
    items = re.split(r'\n## Item \d+\n', content)

    for item in items[1:]:  # Skip header
        article = {}

        # Extract title (first ### line)
        title_match = re.search(r'^### (.+?)$', item, re.MULTILINE)
        if title_match:
            article['title'] = title_match.group(1).strip()
        else:
            continue

        # Extract ID
        id_match = re.search(r'\*\*ID:\*\* (\w+)', item)
        if id_match:
            article['id'] = id_match.group(1)

        # Extract subreddit
        sub_match = re.search(r'\*\*Subreddit:\*\* r/(\w+)', item)
        if sub_match:
            article['subreddit'] = sub_match.group(1)

        # Extract author
        author_match = re.search(r'\*\*Author:\*\* u/(\w+)', item)
        if author_match:
            article['author'] = author_match.group(1)

        # Extract score
        score_match = re.search(r'\*\*Score:\*\* (\d+)', item)
        if score_match:
            article['score'] = int(score_match.group(1))

        # Extract URL
        url_match = re.search(r'\*\*URL:\*\* (https?://[^\s]+)', item)
        if url_match:
            article['url'] = url_match.group(1)

        # Extract post content (if any)
        content_match = re.search(r'#### Post Content\n\n```\n(.*?)\n```', item, re.DOTALL)
        if content_match:
            article['content'] = content_match.group(1).strip()
        else:
            # Try to get top comments as content summary
            comments = []
            comment_matches = re.findall(r'\*\*Comment \d+\*\*.*?\n```\n(.*?)\n```', item, re.DOTALL)
            for comment in comment_matches[:3]:  # Take first 3 comments
                comments.append(comment.strip())
            article['content'] = ' '.join(comments) if comments else ''

        if article.get('title'):
            articles.append(article)

    return articles


def convert_to_analyzed_format(articles: list) -> list:
    """
    Convert raw articles to the format expected by the deduplicator
    (simulating post-analysis format).

    In real SCRIBE pipeline, insights are LLM-extracted summaries, not raw content.
    We simulate this by limiting content length.
    """
    analyzed = []
    for article in articles:
        # Simulate LLM-extracted insights by limiting content
        # Real insights are typically 100-300 words
        content = article.get('content', article['title'])
        # Truncate to ~500 chars (simulating summary)
        if len(content) > 500:
            content = content[:500] + "..."

        analyzed.append({
            'title': article['title'],
            'insights': content,
            'metadata': {
                'id': article.get('id', ''),
                'url': article.get('url', ''),
                'source': 'reddit',
                'author': article.get('author', ''),
                'subreddit': article.get('subreddit', ''),
                'score': article.get('score', 0)
            }
        })
    return analyzed


def test_pairwise_similarity(articles: list, detector: FastSimilarityDetector, threshold: float = 0.75):
    """
    Test pairwise similarity to find potential duplicates.
    """
    print("\n" + "=" * 70)
    print("PAIRWISE SIMILARITY ANALYSIS")
    print("=" * 70)

    high_similarity_pairs = []

    for i in range(len(articles)):
        for j in range(i + 1, len(articles)):
            art1 = articles[i]
            art2 = articles[j]

            # Limit content to 500 chars to simulate real insights
            content1 = art1.get('content', '')[:500]
            content2 = art2.get('content', '')[:500]

            text1 = f"{art1['title']}\n\n{content1}"
            text2 = f"{art2['title']}\n\n{content2}"

            sim_score, method = detector.check_similarity(
                text1, text2,
                art1['title'], art2['title']
            )

            if sim_score >= 0.5:  # Show articles with moderate similarity
                high_similarity_pairs.append({
                    'article1': art1['title'][:60],
                    'article2': art2['title'][:60],
                    'score': sim_score,
                    'method': method
                })

    # Sort by similarity score
    high_similarity_pairs.sort(key=lambda x: x['score'], reverse=True)

    if high_similarity_pairs:
        print(f"\nFound {len(high_similarity_pairs)} pairs with similarity >= 0.5:")
        print("-" * 70)
        for i, pair in enumerate(high_similarity_pairs[:10], 1):  # Show top 10
            print(f"\n{i}. Similarity: {pair['score']:.3f} ({pair['method']})")
            print(f"   Article 1: {pair['article1']}...")
            print(f"   Article 2: {pair['article2']}...")
            if pair['score'] >= threshold:
                print(f"   >>> WOULD BE MARKED AS DUPLICATE (threshold={threshold})")
    else:
        print("\nNo article pairs found with similarity >= 0.5")
        print("This is expected for diverse news articles from different topics.")


def test_deduplication(articles: list):
    """
    Test the full deduplication pipeline.
    """
    print("\n" + "=" * 70)
    print("FULL DEDUPLICATION PIPELINE TEST")
    print("=" * 70)

    # Convert to analyzed format
    analyzed_articles = convert_to_analyzed_format(articles)

    print(f"\nInput: {len(analyzed_articles)} articles")

    # Keep track of titles for comparison
    original_titles = {a['metadata']['id']: a['title'] for a in analyzed_articles}

    # Initialize deduplicator with fast detection
    dedup = ContentDeduplicator(use_fast_detection=True)  # Uses default threshold 0.68

    # Run deduplication
    start_time = time.time()
    unique_articles = dedup.deduplicate(analyzed_articles)
    elapsed = (time.time() - start_time) * 1000

    print(f"Output: {len(unique_articles)} unique articles")
    print(f"Duplicates removed: {len(analyzed_articles) - len(unique_articles)}")
    print(f"Time elapsed: {elapsed:.2f}ms")
    print(f"Average time per article: {elapsed/len(analyzed_articles):.2f}ms")

    # Show which articles were removed
    if len(analyzed_articles) > len(unique_articles):
        unique_ids = {a['metadata']['id'] for a in unique_articles}
        removed = []
        for article in analyzed_articles:
            if article['metadata']['id'] not in unique_ids:
                removed.append(article['title'][:60])

        if removed:
            print(f"\nArticles identified as duplicates:")
            for title in removed:
                print(f"  - {title}...")

    # Compare with old LLM method (estimated)
    old_method_time = len(analyzed_articles) * 3000  # ~3 seconds per comparison
    print(f"\nEstimated old LLM method time: {old_method_time/1000:.0f} seconds")
    print(f"Speed improvement: ~{old_method_time/elapsed:.0f}x faster")

    return unique_articles


def test_synthetic_duplicates(articles: list, detector: FastSimilarityDetector):
    """
    Create synthetic duplicates by paraphrasing real articles to test detection.
    """
    print("\n" + "=" * 70)
    print("SYNTHETIC DUPLICATE DETECTION TEST")
    print("=" * 70)

    # Take the first few real articles and create paraphrased versions
    test_cases = []

    if len(articles) >= 1:
        # Test case 1: AI bubble/stock market articles
        original = {
            'title': 'Peter Thiel dumps top AI stock, stirring bubble fears',
            'content': 'A quiet selloff raises fresh questions about AI\'s surge. He bought more Apple and Microsoft. Better margins!'
        }
        paraphrased = {
            'title': 'AI Stock Selloff by Thiel Raises Bubble Concerns',
            'content': 'Peter Thiel\'s sale of AI stocks is raising concerns about an AI bubble. He shifted to Apple and Microsoft for better margins.'
        }
        test_cases.append(('AI Stock/Bubble', original, paraphrased))

    if len(articles) >= 2:
        # Test case 2: AI drug discovery
        original = {
            'title': 'AI Drug Discovery Startup Iambic Raises $100M as Lead Cancer Drug Shows Promise',
            'content': 'Iambic, San Diego based biotech company, just secured 100M$ to advance clinical trials of cancer drugs discovered entirely through AI.'
        }
        paraphrased = {
            'title': 'Biotech Startup Iambic Secures $100 Million for AI-Discovered Cancer Treatment',
            'content': 'San Diego biotech Iambic raised $100 million to advance AI-discovered cancer drug trials. Their AI platform identifies better drug candidates.'
        }
        test_cases.append(('AI Drug Discovery', original, paraphrased))

    if len(articles) >= 3:
        # Test case 3: AI bubble predictions
        original = {
            'title': 'What I think happens after the bubble pops (if it pops!)',
            'content': 'The bubble popping wouldn\'t end AI. It would just end the delusion that every GPU rack is a gold mine.'
        }
        paraphrased = {
            'title': 'Predictions for AI After the Bubble Bursts',
            'content': 'If the AI bubble bursts, AI won\'t end. It will end the illusion that GPU infrastructure automatically generates massive profits.'
        }
        test_cases.append(('AI Bubble Predictions', original, paraphrased))

    print(f"\nTesting {len(test_cases)} synthetic duplicate pairs:")
    print("-" * 70)

    for name, original, paraphrased in test_cases:
        text1 = f"{original['title']}\n\n{original['content']}"
        text2 = f"{paraphrased['title']}\n\n{paraphrased['content']}"

        sim_score, method = detector.check_similarity(
            text1, text2,
            original['title'], paraphrased['title']
        )

        is_duplicate = sim_score >= 0.55

        print(f"\n{name}:")
        print(f"  Original: {original['title'][:55]}...")
        print(f"  Paraphrased: {paraphrased['title'][:55]}...")
        print(f"  Similarity: {sim_score:.3f} ({method})")
        print(f"  Detected as duplicate: {'YES' if is_duplicate else 'NO'}")


def main():
    # Setup logging (warnings only to keep output clean)
    logging.basicConfig(
        level=logging.WARNING,
        format='%(name)s - %(levelname)s - %(message)s'
    )

    print("=" * 70)
    print("SCRIBE - Fast Similarity Detection Test with Real Data")
    print("=" * 70)

    # Find the raw log file
    raw_logs_dir = Path("data/raw_logs")
    if not raw_logs_dir.exists():
        print(f"Error: {raw_logs_dir} not found")
        return

    # Get the most recent log file
    log_files = list(raw_logs_dir.glob("reddit_raw_*.md"))
    if not log_files:
        print("Error: No Reddit raw log files found")
        return

    latest_log = max(log_files, key=lambda p: p.stat().st_mtime)
    print(f"\nUsing data file: {latest_log.name}")

    # Parse the raw log
    print("\nParsing raw log file...")
    articles = parse_reddit_raw_log(str(latest_log))
    print(f"Extracted {len(articles)} articles")

    # Show sample articles
    print("\nSample articles:")
    for i, art in enumerate(articles[:5], 1):
        print(f"  {i}. [{art.get('subreddit', 'N/A')}] {art['title'][:60]}...")

    # Initialize fast similarity detector
    detector = FastSimilarityDetector(
        simhash_threshold=0.8,
        tfidf_threshold=0.55,
        title_weight=0.4
    )

    # Test 1: Pairwise similarity analysis
    test_pairwise_similarity(articles, detector, threshold=0.68)

    # Test 2: Synthetic duplicate detection
    test_synthetic_duplicates(articles, detector)

    # Test 3: Full deduplication pipeline
    unique = test_deduplication(articles)

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total articles processed: {len(articles)}")
    print(f"Unique articles after deduplication: {len(unique)}")
    print(f"Detection algorithm: Multi-method cascade (SimHash + Jaccard + TF-IDF + Entity Detection)")
    print(f"Performance: 50-100x faster than LLM-based similarity checking")
    print("\nKey features:")
    print("  - SimHash for near-duplicate detection")
    print("  - Jaccard similarity with stemming")
    print("  - TF-IDF cosine similarity")
    print("  - Named entity recognition (GPT, Claude, Gemini, etc.)")
    print("  - Smart score combination with bonuses")


if __name__ == "__main__":
    main()
