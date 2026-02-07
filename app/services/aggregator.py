"""
Pure Python data aggregation for report components.

Handles heatmap, entity tracking, and market pulse calculations.
No AI calls — these are deterministic counting/grouping operations.
"""
import json
from collections import defaultdict, Counter
from typing import List, Dict


class ReportAggregator:
    """Aggregates article data into visualization-ready structures."""

    @staticmethod
    def aggregate_sector_heatmap(articles: List[dict]) -> List[dict]:
        """
        Aggregate articles by business line and sentiment for heatmap.

        Groups articles by business_line, counts positive/negative/neutral sentiment,
        and determines overall directional signal per sector.

        Args:
            articles: List of prepared article dicts (with business_line and sentiment keys)

        Returns:
            List of dicts sorted by article_count descending:
            [{"sector": str, "signal": str, "signal_class": str, "article_count": int}, ...]
        """
        sector_data = defaultdict(lambda: {"positive": 0, "negative": 0, "neutral": 0})

        for article in articles:
            bl = article.get("business_line")
            sentiment = article.get("sentiment")
            if bl and sentiment:
                sector_data[bl][sentiment] += 1

        heatmap_cells = []
        for sector, sentiments in sector_data.items():
            pos = sentiments["positive"]
            neg = sentiments["negative"]

            if pos > neg:
                signal = "Favorable trends"
                signal_class = "heat-positive"
            elif neg > pos:
                signal = "Risk indicators"
                signal_class = "heat-negative"
            else:
                signal = "Mixed signals"
                signal_class = "heat-neutral"

            heatmap_cells.append({
                "sector": sector,
                "signal": signal,
                "signal_class": signal_class,
                "article_count": sum(sentiments.values()),
            })

        return sorted(heatmap_cells, key=lambda x: x["article_count"], reverse=True)

    @staticmethod
    def aggregate_entity_tracker(articles: List[dict], top_n: int = 15) -> List[dict]:
        """
        Count entity mentions across all articles.

        Parses the entities field from each article (already a list of dicts
        from _prepare_articles), counts occurrences of each entity name,
        and returns the top N ranked by count.

        Args:
            articles: List of prepared article dicts (entities field is List[dict])
            top_n: Maximum number of entities to return (default 15)

        Returns:
            List of dicts sorted by count descending:
            [{"name": str, "count": int, "type": str}, ...]
        """
        entity_counts = defaultdict(lambda: {"count": 0, "type": None})

        for article in articles:
            entities = article.get("entities", [])
            # Handle case where entities might still be a JSON string
            if isinstance(entities, str):
                try:
                    entities = json.loads(entities)
                except (json.JSONDecodeError, TypeError):
                    entities = []
            elif entities is None:
                entities = []

            for entity in entities:
                if isinstance(entity, dict) and "name" in entity:
                    name = entity["name"]
                    entity_counts[name]["count"] += 1
                    if entity.get("type"):
                        entity_counts[name]["type"] = entity["type"]

        entity_list = [
            {"name": name, "count": data["count"], "type": data["type"]}
            for name, data in entity_counts.items()
        ]

        return sorted(entity_list, key=lambda x: x["count"], reverse=True)[:top_n]
