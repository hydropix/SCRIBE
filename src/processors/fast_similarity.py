"""Fast similarity detection using multiple algorithms"""

import logging
import re
from typing import List, Dict, Any, Tuple, Optional
from collections import defaultdict
import hashlib


class FastSimilarityDetector:
    """
    Fast similarity detection using multiple algorithms in cascade.
    Much faster than LLM-based similarity checking.
    """

    def __init__(
        self,
        simhash_threshold: float = 0.85,
        tfidf_threshold: float = 0.5,
        title_weight: float = 0.4,
        use_embeddings: bool = False
    ):
        """
        Initialize the fast similarity detector.

        Args:
            simhash_threshold: Threshold for SimHash similarity (0-1)
            tfidf_threshold: Threshold for TF-IDF cosine similarity (0-1)
            title_weight: Weight given to title vs content (0-1)
            use_embeddings: Whether to use sentence embeddings (slower but more accurate)
        """
        self.logger = logging.getLogger("SCRIBE.FastSimilarity")
        self.simhash_threshold = simhash_threshold
        self.tfidf_threshold = tfidf_threshold
        self.title_weight = title_weight
        self.use_embeddings = use_embeddings

        # Lazy loading of ML components
        self._vectorizer = None
        self._tfidf_matrix = None
        self._corpus_texts = []
        self._corpus_hashes = {}
        self._embedding_model = None
        self._embeddings_cache = {}

        self.logger.info(
            f"FastSimilarityDetector initialized "
            f"(simhash={simhash_threshold}, tfidf={tfidf_threshold})"
        )

    def _tokenize(self, text: str, use_stemming: bool = True) -> List[str]:
        """
        Tokenize text into words for similarity analysis.

        Args:
            text: Input text
            use_stemming: Apply simple suffix stripping for better matching

        Returns:
            List of tokens
        """
        # Lowercase and extract words
        text = text.lower()
        # Remove special characters, keep alphanumeric and spaces
        text = re.sub(r'[^a-z0-9\s]', ' ', text)
        # Split into words and filter empty
        tokens = [w.strip() for w in text.split() if len(w.strip()) > 2]

        if use_stemming:
            # Simple suffix stripping (poor man's stemming)
            # This helps match "improved" with "improvement", "capabilities" with "capability", etc.
            stemmed = []
            for token in tokens:
                # Remove common suffixes
                stem = token
                for suffix in ['ing', 'ment', 'tion', 'sion', 'ness', 'able', 'ible', 'ity', 'ies', 'ance', 'ence', 'ly', 'ed', 'es', 's']:
                    if len(stem) > 5 and stem.endswith(suffix):
                        stem = stem[:-len(suffix)]
                        break
                stemmed.append(stem)
            return stemmed

        return tokens

    def _compute_simhash(self, text: str, hash_bits: int = 64) -> int:
        """
        Compute SimHash fingerprint for text.
        SimHash is locality-sensitive: similar texts have similar hashes.

        Args:
            text: Input text
            hash_bits: Number of bits in the hash

        Returns:
            SimHash integer value
        """
        tokens = self._tokenize(text)
        if not tokens:
            return 0

        # Initialize bit weights
        bit_weights = [0] * hash_bits

        for token in tokens:
            # Hash each token
            token_hash = int(hashlib.md5(token.encode('utf-8')).hexdigest(), 16)

            # Update bit weights based on token hash
            for i in range(hash_bits):
                bit = (token_hash >> i) & 1
                if bit:
                    bit_weights[i] += 1
                else:
                    bit_weights[i] -= 1

        # Generate final hash from bit weights
        simhash = 0
        for i in range(hash_bits):
            if bit_weights[i] > 0:
                simhash |= (1 << i)

        return simhash

    def _simhash_similarity(self, hash1: int, hash2: int, hash_bits: int = 64) -> float:
        """
        Calculate similarity between two SimHash values.

        Args:
            hash1: First SimHash
            hash2: Second SimHash
            hash_bits: Number of bits

        Returns:
            Similarity score (0-1)
        """
        # Count differing bits (Hamming distance)
        xor_result = hash1 ^ hash2
        hamming_distance = bin(xor_result).count('1')

        # Convert to similarity score
        similarity = 1 - (hamming_distance / hash_bits)
        return similarity

    def _compute_tfidf_similarity(self, text1: str, text2: str) -> float:
        """
        Compute TF-IDF cosine similarity between two texts.

        Args:
            text1: First text
            text2: Second text

        Returns:
            Cosine similarity score (0-1)
        """
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity
        except ImportError:
            self.logger.warning("scikit-learn not installed, skipping TF-IDF")
            return 0.0

        # Create a simple vectorizer for pairwise comparison
        vectorizer = TfidfVectorizer(
            lowercase=True,
            stop_words='english',
            max_features=1000,
            ngram_range=(1, 2)
        )

        try:
            tfidf_matrix = vectorizer.fit_transform([text1, text2])
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
            return float(similarity)
        except Exception as e:
            self.logger.debug(f"TF-IDF error: {e}")
            return 0.0

    def _compute_jaccard_similarity(self, text1: str, text2: str) -> float:
        """
        Compute Jaccard similarity between two texts (word overlap).

        Args:
            text1: First text
            text2: Second text

        Returns:
            Jaccard similarity score (0-1)
        """
        tokens1 = set(self._tokenize(text1))
        tokens2 = set(self._tokenize(text2))

        if not tokens1 or not tokens2:
            return 0.0

        intersection = len(tokens1 & tokens2)
        union = len(tokens1 | tokens2)

        return intersection / union if union > 0 else 0.0

    def _title_similarity(self, title1: str, title2: str) -> float:
        """
        Compute similarity between titles using multiple methods.

        Args:
            title1: First title
            title2: Second title

        Returns:
            Similarity score (0-1)
        """
        # Exact match (case-insensitive)
        if title1.lower().strip() == title2.lower().strip():
            return 1.0

        # Jaccard similarity for titles
        jaccard = self._compute_jaccard_similarity(title1, title2)

        # Character-level similarity (for typos, minor variations)
        try:
            from difflib import SequenceMatcher
            char_sim = SequenceMatcher(None, title1.lower(), title2.lower()).ratio()
        except Exception:
            char_sim = jaccard

        # Return weighted average
        return max(jaccard, char_sim)

    def check_similarity(
        self,
        text1: str,
        text2: str,
        title1: str = "",
        title2: str = ""
    ) -> Tuple[float, str]:
        """
        Check similarity between two contents using cascade of fast methods.

        Args:
            text1: First content text
            text2: Second content text
            title1: First title (optional)
            title2: Second title (optional)

        Returns:
            Tuple of (similarity_score, method_used)
        """
        # Step 1: Title similarity (very fast)
        title_sim = 0.0
        if title1 and title2:
            title_sim = self._title_similarity(title1, title2)
            if title_sim >= 0.95:
                return (title_sim, "exact_title")
            if title_sim >= 0.8:
                # High title similarity, likely duplicate
                return (title_sim * 0.95, "title_match")

        # Step 2: SimHash (ultra-fast, good for near-duplicates)
        hash1 = self._compute_simhash(text1)
        hash2 = self._compute_simhash(text2)
        simhash_sim = self._simhash_similarity(hash1, hash2)

        if simhash_sim >= self.simhash_threshold:
            return (simhash_sim, "simhash")

        # Step 3: Jaccard similarity (fast, word overlap)
        jaccard_sim = self._compute_jaccard_similarity(text1, text2)
        if jaccard_sim >= 0.6:
            return (jaccard_sim, "jaccard")

        # Step 4: TF-IDF cosine similarity (moderate speed, good accuracy)
        tfidf_sim = self._compute_tfidf_similarity(text1, text2)
        if tfidf_sim >= self.tfidf_threshold:
            return (tfidf_sim, "tfidf")

        # Step 5: Smart combination for semantic similarity
        # Use weighted combination of all signals
        content_sim = max(simhash_sim, jaccard_sim, tfidf_sim)

        # Step 6: Check for key entity overlap (important for news articles)
        # If both texts mention the same product/model names, they're likely about the same topic
        key_entities = self._extract_key_entities(text1, text2)

        # Step 7: Check for specific number overlap (strong indicator of same news story)
        number_overlap = self._calculate_number_overlap(text1, text2)

        # Reduce entity bonus for very long texts (they naturally contain more entities)
        # This prevents false positives on long comprehensive articles
        avg_length = (len(text1) + len(text2)) / 2
        length_penalty = 1.0
        if avg_length > 2000:
            length_penalty = 0.3  # Reduce bonus for very long texts
        elif avg_length > 1000:
            length_penalty = 0.6  # Moderate reduction for medium texts

        entity_bonus = 0.0
        if key_entities >= 3:
            entity_bonus = 0.12 * length_penalty
        elif key_entities >= 2:
            entity_bonus = 0.08 * length_penalty
        elif key_entities == 1:
            entity_bonus = 0.04 * length_penalty

        # Number overlap bonus (very strong signal for same news story)
        number_bonus = 0.0
        if number_overlap >= 0.5:
            number_bonus = 0.15  # Strong overlap of specific numbers
        elif number_overlap >= 0.3:
            number_bonus = 0.08

        if title1 and title2:
            # Title similarity is very important for detecting same-topic articles
            # Require HIGHER title similarity (>0.6) AND good content overlap for smart combination
            if title_sim >= 0.6 and content_sim >= 0.4:
                # Boost score when both title and content show strong similarity
                combined = (
                    self.title_weight * title_sim +
                    (1 - self.title_weight) * content_sim +
                    entity_bonus +
                    number_bonus +
                    0.08  # Smaller bonus to reduce false positives
                )
                combined = min(combined, 1.0)  # Cap at 1.0
                return (combined, "smart_combined")

            combined = (
                self.title_weight * title_sim +
                (1 - self.title_weight) * content_sim +
                entity_bonus +
                number_bonus
            )
        else:
            combined = content_sim + entity_bonus + number_bonus

        combined = min(combined, 1.0)  # Cap at 1.0
        return (combined, "combined")

    def _extract_key_entities(self, text1: str, text2: str) -> int:
        """
        Count shared key entities (product names, models, companies) between texts.

        Args:
            text1: First text
            text2: Second text

        Returns:
            Number of shared key entities
        """
        # Common AI-related key terms (case-insensitive)
        key_patterns = [
            r'\bgpt-?\d+\b',  # GPT-4, GPT-5, GPT5
            r'\bclaude[- ]?\d+\.?\d*\b',  # Claude 3, Claude 3.5
            r'\bgemini[- ]?\d+\.?\d*\b',  # Gemini 1.5, Gemini 2.0
            r'\bllama[- ]?\d+\b',  # Llama 2, Llama 3
            r'\bmistral\b',
            r'\bopenai\b',
            r'\banthrop\w*\b',  # anthropic
            r'\bgoogle\b',
            r'\bmeta\b',
            r'\bdeepseek\b',
            r'\bqwen\b',
            r'\bvit\b',  # Vision Transformer
            r'\btransform\w*\b',  # transformer
            r'\bdiffusion\b',
            r'\bsora\b',
            r'\bdalle\b',
            r'\bmidjourney\b',
        ]

        text1_lower = text1.lower()
        text2_lower = text2.lower()

        shared_count = 0
        for pattern in key_patterns:
            if re.search(pattern, text1_lower) and re.search(pattern, text2_lower):
                shared_count += 1

        # Also extract proper nouns (capitalized words) that appear in both texts
        # This helps detect company/product names not in the predefined list
        proper_nouns1 = set(re.findall(r'\b[A-Z][a-z]+(?:[A-Z][a-z]+)*\b', text1))
        proper_nouns2 = set(re.findall(r'\b[A-Z][a-z]+(?:[A-Z][a-z]+)*\b', text2))
        # Filter out common words
        common_words = {'The', 'This', 'That', 'What', 'How', 'When', 'Where', 'Why', 'Which'}
        proper_nouns1 -= common_words
        proper_nouns2 -= common_words
        shared_proper_nouns = proper_nouns1 & proper_nouns2

        # Add shared proper nouns (each one counts)
        shared_count += len(shared_proper_nouns)

        # Also check for alphanumeric codes (like IAM1363, HER2)
        codes1 = set(re.findall(r'\b[A-Z]{2,}[\d]+\b', text1))
        codes2 = set(re.findall(r'\b[A-Z]{2,}[\d]+\b', text2))
        shared_codes = codes1 & codes2
        shared_count += len(shared_codes) * 2  # Codes are strong indicators

        return shared_count

    def _extract_specific_numbers(self, text: str) -> set:
        """
        Extract specific numbers/amounts from text (funding amounts, percentages, etc.)
        These are strong indicators of the same news story.

        Args:
            text: Input text

        Returns:
            Set of specific numbers found
        """
        numbers = set()

        # Money amounts (e.g., $100M, $50 billion)
        money_pattern = r'\$\d+(?:\.\d+)?(?:\s*(?:M|B|million|billion|thousand|k))?'
        numbers.update(re.findall(money_pattern, text.lower()))

        # Percentages
        percent_pattern = r'\d+(?:\.\d+)?%'
        numbers.update(re.findall(percent_pattern, text))

        # Specific numbers like "40%" or "100 million"
        specific_pattern = r'\b\d{2,}\b'  # Numbers with 2+ digits
        numbers.update(re.findall(specific_pattern, text))

        return numbers

    def _calculate_number_overlap(self, text1: str, text2: str) -> float:
        """
        Calculate overlap of specific numbers between texts.
        High overlap indicates same news story.

        Returns:
            Overlap score (0-1)
        """
        nums1 = self._extract_specific_numbers(text1)
        nums2 = self._extract_specific_numbers(text2)

        if not nums1 or not nums2:
            return 0.0

        intersection = len(nums1 & nums2)
        if intersection == 0:
            return 0.0

        # Use min to get overlap ratio
        min_size = min(len(nums1), len(nums2))
        return intersection / min_size

    def is_duplicate(
        self,
        new_text: str,
        existing_texts: List[str],
        new_title: str = "",
        existing_titles: List[str] = None,
        threshold: float = None
    ) -> Tuple[bool, float, int]:
        """
        Check if new content is a duplicate of any existing content.

        Args:
            new_text: New content text
            existing_texts: List of existing content texts
            new_title: New content title (optional)
            existing_titles: List of existing titles (optional)
            threshold: Custom similarity threshold (uses tfidf_threshold if None)

        Returns:
            Tuple of (is_duplicate, max_similarity, index_of_most_similar)
        """
        if threshold is None:
            threshold = self.tfidf_threshold

        if existing_titles is None:
            existing_titles = [""] * len(existing_texts)

        max_similarity = 0.0
        most_similar_idx = -1

        for i, (existing_text, existing_title) in enumerate(zip(existing_texts, existing_titles)):
            sim_score, method = self.check_similarity(
                new_text, existing_text,
                new_title, existing_title
            )

            if sim_score > max_similarity:
                max_similarity = sim_score
                most_similar_idx = i

            # Early exit if we found a clear duplicate
            if sim_score >= threshold:
                self.logger.debug(
                    f"Duplicate found via {method}: {sim_score:.3f} >= {threshold}"
                )
                return (True, sim_score, i)

        return (False, max_similarity, most_similar_idx)

    def batch_deduplicate(
        self,
        contents: List[Dict[str, Any]],
        title_key: str = 'title',
        text_key: str = 'insights',
        threshold: float = None
    ) -> List[Dict[str, Any]]:
        """
        Deduplicate a batch of contents efficiently.

        Args:
            contents: List of content dictionaries
            title_key: Key for title field
            text_key: Key for text field
            threshold: Similarity threshold for duplicates

        Returns:
            List of unique contents
        """
        if not contents:
            return []

        if threshold is None:
            threshold = self.tfidf_threshold

        unique_contents = []
        unique_texts = []
        unique_titles = []

        for content in contents:
            title = content.get(title_key, "")
            text = content.get(text_key, "")

            # Combine title and text for comparison
            full_text = f"{title}\n\n{text}" if text else title

            if not unique_texts:
                # First content is always unique
                unique_contents.append(content)
                unique_texts.append(full_text)
                unique_titles.append(title)
                continue

            # Check against existing unique contents
            is_dup, sim_score, _ = self.is_duplicate(
                full_text, unique_texts,
                title, unique_titles,
                threshold
            )

            if not is_dup:
                unique_contents.append(content)
                unique_texts.append(full_text)
                unique_titles.append(title)

        return unique_contents

    def get_similarity_matrix(
        self,
        texts: List[str],
        titles: List[str] = None
    ) -> List[List[float]]:
        """
        Compute pairwise similarity matrix for all texts.

        Args:
            texts: List of texts
            titles: List of titles (optional)

        Returns:
            NxN similarity matrix
        """
        n = len(texts)
        if titles is None:
            titles = [""] * n

        matrix = [[0.0] * n for _ in range(n)]

        for i in range(n):
            matrix[i][i] = 1.0  # Self-similarity
            for j in range(i + 1, n):
                sim, _ = self.check_similarity(texts[i], texts[j], titles[i], titles[j])
                matrix[i][j] = sim
                matrix[j][i] = sim  # Symmetric

        return matrix


if __name__ == "__main__":
    # Quick test
    logging.basicConfig(level=logging.DEBUG)

    detector = FastSimilarityDetector()

    # Test cases
    test_cases = [
        (
            "GPT-5 Released with Improved Reasoning",
            "OpenAI released GPT-5 with significantly improved reasoning capabilities.",
            "OpenAI Announces GPT-5",
            "GPT-5 has been released by OpenAI with better reasoning abilities."
        ),
        (
            "New Vision Transformer Published",
            "Researchers published a new ViT architecture achieving SOTA on ImageNet.",
            "GPT-5 Released",
            "OpenAI released GPT-5 with improved reasoning."
        ),
        (
            "Identical Title Test",
            "This is the exact same content word for word.",
            "Identical Title Test",
            "This is the exact same content word for word."
        )
    ]

    print("Testing Fast Similarity Detection")
    print("=" * 50)

    for i, (title1, text1, title2, text2) in enumerate(test_cases):
        print(f"\nTest {i + 1}:")
        print(f"  Title 1: {title1}")
        print(f"  Title 2: {title2}")

        sim_score, method = detector.check_similarity(text1, text2, title1, title2)
        print(f"  Similarity: {sim_score:.3f} (via {method})")
        print(f"  Is Duplicate: {sim_score >= 0.85}")

    # Batch deduplication test
    print("\n" + "=" * 50)
    print("Batch Deduplication Test")

    test_contents = [
        {
            'title': 'GPT-5 Released',
            'insights': 'OpenAI released GPT-5 with improved reasoning capabilities.'
        },
        {
            'title': 'OpenAI Announces GPT-5',
            'insights': 'GPT-5 has been released by OpenAI with better reasoning.'
        },
        {
            'title': 'New Vision Transformer',
            'insights': 'Researchers published a new ViT architecture.'
        }
    ]

    unique = detector.batch_deduplicate(test_contents)
    print(f"\nOriginal: {len(test_contents)} contents")
    print(f"After deduplication: {len(unique)} contents")
    for c in unique:
        print(f"  - {c['title']}")
