"""
Semantic deduplication service for news articles.

Uses sentence transformers to identify semantically similar articles
across different sources and merge them into single entries.
"""

import structlog
from datetime import datetime
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer, util


logger = structlog.get_logger(service="deduplicator")


class _UnionFind:
    """Disjoint set data structure for grouping similar articles."""

    def __init__(self, n: int):
        self.parent = list(range(n))

    def find(self, x: int) -> int:
        """Find the root parent of element x with path compression."""
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]  # Path compression
            x = self.parent[x]
        return x

    def union(self, x: int, y: int) -> None:
        """Merge the sets containing x and y."""
        px, py = self.find(x), self.find(y)
        if px != py:
            self.parent[px] = py


class ArticleDeduplicator:
    """
    Identifies and merges semantically similar articles using sentence transformers.

    Uses cosine similarity on article title + description embeddings to find duplicates.
    Articles with similarity >= threshold are grouped and merged.
    """

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        similarity_threshold: float = 0.85
    ):
        """
        Initialize deduplicator with model configuration.

        Args:
            model_name: Sentence transformer model to use. Default is all-MiniLM-L6-v2
                       (fast, 80MB, good accuracy for headline similarity).
            similarity_threshold: Cosine similarity threshold (0-1) above which articles
                                are considered duplicates. Default 0.85.
        """
        self.model_name = model_name
        self.similarity_threshold = similarity_threshold
        self._model: Optional[SentenceTransformer] = None

        logger.info(
            "deduplicator_initialized",
            model=model_name,
            threshold=similarity_threshold
        )

    def _load_model(self) -> None:
        """Lazily load the sentence transformer model on first use."""
        if self._model is None:
            logger.info("loading_model", model=self.model_name)
            self._model = SentenceTransformer(self.model_name)
            logger.info("model_loaded", model=self.model_name)

    def deduplicate(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Deduplicate a list of articles by semantic similarity.

        Articles with similarity >= threshold are grouped together.
        For each group, the earliest article (by published_at) is kept as the
        representative, with sources merged and the longest description retained.

        Args:
            articles: List of article dictionaries with keys:
                     - title (str): Article headline
                     - description (str, optional): Article summary/description
                     - source_name (str): Publication source
                     - published_at (datetime, optional): Publication date

        Returns:
            List of deduplicated articles with merged source_name for duplicates.
        """
        # Early return for empty or single-article lists
        if len(articles) <= 1:
            logger.info("deduplication_skipped", count=len(articles), reason="too_few_articles")
            return articles

        # Ensure model is loaded
        self._load_model()

        # Generate text representation for each article
        texts = [
            f"{article['title']} {article.get('description', '')}"
            for article in articles
        ]

        # Encode all texts to embeddings
        logger.debug("encoding_articles", count=len(articles))
        embeddings = self._model.encode(texts, convert_to_tensor=True)

        # Compute pairwise cosine similarity
        cos_scores = util.cos_sim(embeddings, embeddings)

        # Use Union-Find to group similar articles
        uf = _UnionFind(len(articles))
        duplicate_pairs = 0

        for i in range(len(articles)):
            for j in range(i + 1, len(articles)):
                similarity = cos_scores[i][j].item()
                if similarity >= self.similarity_threshold:
                    uf.union(i, j)
                    duplicate_pairs += 1
                    logger.debug(
                        "duplicate_detected",
                        article1=articles[i]['title'][:50],
                        article2=articles[j]['title'][:50],
                        similarity=round(similarity, 3)
                    )

        # Group articles by their root parent
        groups: Dict[int, List[int]] = {}
        for i in range(len(articles)):
            root = uf.find(i)
            if root not in groups:
                groups[root] = []
            groups[root].append(i)

        # Merge each group
        deduplicated = []
        large_groups = 0

        for group_indices in groups.values():
            if len(group_indices) > 1:
                # Multiple articles in this group - merge them
                merged = self._merge_articles(articles, group_indices)
                deduplicated.append(merged)

                if len(group_indices) >= 3:
                    large_groups += 1
                    logger.debug(
                        "large_duplicate_group",
                        size=len(group_indices),
                        title=merged['title'][:50],
                        sources=merged['source_name']
                    )
            else:
                # Single article in group - keep as is
                deduplicated.append(articles[group_indices[0]])

        logger.info(
            "deduplication_complete",
            input_count=len(articles),
            output_count=len(deduplicated),
            duplicates_removed=len(articles) - len(deduplicated),
            duplicate_pairs=duplicate_pairs,
            large_groups=large_groups
        )

        return deduplicated

    def _merge_articles(
        self,
        articles: List[Dict[str, Any]],
        indices: List[int]
    ) -> Dict[str, Any]:
        """
        Merge a group of duplicate articles into a single representative article.

        Selection strategy:
        - Keep article with earliest published_at as base
        - Merge all unique source_name values (comma-separated)
        - Use longest description from the group

        Args:
            articles: Full list of articles
            indices: Indices of articles to merge

        Returns:
            Merged article dictionary
        """
        group_articles = [articles[i] for i in indices]

        # Sort by published_at (None values go to end)
        sorted_articles = sorted(
            group_articles,
            key=lambda a: a.get('published_at') or datetime.max
        )

        # Use earliest article as base
        keeper = sorted_articles[0].copy()

        # Merge source names (unique, preserve order)
        sources = []
        seen_sources = set()
        for article in sorted_articles:
            source = article['source_name']
            if source not in seen_sources:
                sources.append(source)
                seen_sources.add(source)

        keeper['source_name'] = ", ".join(sources)

        # Use longest description
        descriptions = [
            article.get('description', '')
            for article in sorted_articles
            if article.get('description')
        ]
        if descriptions:
            keeper['description'] = max(descriptions, key=len)

        return keeper
