from __future__ import annotations

"""
Property of Data-Blitz Inc.
Author: Paul Harvener

Catalog search service backed by Elasticsearch with deterministic fallback.
"""

import json
import os
import time
from pathlib import Path
from typing import Any

from elasticsearch import Elasticsearch, helpers

from app.models import ProductResult, QueryIntent


class CatalogService:
    # Args:
    #   None
    # Returns:
    #   None
    # Notes:
    #   Reads Elasticsearch connection options and preloads fallback catalog docs.
    def __init__(self) -> None:
        self.es_url = os.getenv("ELASTICSEARCH_URL", "http://elasticsearch:9200")
        self.es_index = os.getenv("ELASTICSEARCH_INDEX", "digikey_products")
        self.es_username = os.getenv("ELASTICSEARCH_USERNAME") or None
        self.es_password = os.getenv("ELASTICSEARCH_PASSWORD") or None
        self.connect_attempts = int(os.getenv("ELASTICSEARCH_CONNECT_ATTEMPTS", "5"))
        self.connect_sleep_seconds = float(os.getenv("ELASTICSEARCH_CONNECT_SLEEP_SECONDS", "1.0"))

        self._client: Elasticsearch | None = None
        self._mode = "fallback"
        self._fallback_docs = self._load_seed_catalog()

    # Args:
    #   None
    # Returns:
    #   str
    #     Current catalog mode indicator.
    @property
    def mode(self) -> str:
        return self._mode

    # Args:
    #   None
    # Returns:
    #   str | None
    #     Warning text when Elasticsearch is unavailable; otherwise None.
    # Notes:
    #   Initializes index/mapping and seeds data if index is empty.
    def initialize(self) -> str | None:
        client = self._connect_with_retry(
            max_attempts=self.connect_attempts,
            sleep_seconds=self.connect_sleep_seconds,
        )
        if client is None:
            self._mode = "fallback"
            return "Elasticsearch is unavailable; using local fallback catalog."

        self._client = client
        self._ensure_index()
        self._seed_if_empty()
        self._mode = "elasticsearch"
        return None

    # Args:
    #   intent: QueryIntent
    #     Parsed user intent with constraints and sort preference.
    # Returns:
    #   tuple[list[ProductResult], str | None]
    #     Product list and optional warning string.
    # Notes:
    #   Uses Elasticsearch when available and automatically falls back on error.
    def search(self, intent: QueryIntent) -> tuple[list[ProductResult], str | None]:
        if self._mode != "elasticsearch" or self._client is None:
            return self._fallback_search(intent), "Results are from fallback data, not Elasticsearch."

        try:
            return self._search_elasticsearch(intent), None
        except Exception as exc:
            return self._fallback_search(intent), f"Elasticsearch query failed ({exc}); using fallback data."

    # Args:
    #   max_attempts: int
    #     Number of ping attempts.
    #   sleep_seconds: float
    #     Delay between attempts.
    # Returns:
    #   Elasticsearch | None
    #     Connected Elasticsearch client or None after timeout.
    def _connect_with_retry(self, max_attempts: int, sleep_seconds: float) -> Elasticsearch | None:
        auth = (self.es_username, self.es_password) if self.es_username and self.es_password else None

        for _ in range(max_attempts):
            try:
                client = Elasticsearch(self.es_url, basic_auth=auth, request_timeout=15)
                if client.ping():
                    return client
            except Exception:
                pass
            time.sleep(sleep_seconds)
        return None

    # Args:
    #   None
    # Returns:
    #   None
    # Notes:
    #   Creates the product index with mapping if it does not exist.
    def _ensure_index(self) -> None:
        assert self._client is not None
        if self._client.indices.exists(index=self.es_index):
            return

        mapping = {
            "mappings": {
                "properties": {
                    "id": {"type": "keyword"},
                    "manufacturer": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                    "manufacturer_part_number": {"type": "keyword"},
                    "name": {"type": "text"},
                    "description": {"type": "text"},
                    "category": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                    "unit_price": {"type": "float"},
                    "quantity_available": {"type": "integer"},
                    "tags": {"type": "text"},
                    "use_cases": {"type": "text"},
                    "spec_blob": {"type": "text"},
                    "product_url": {"type": "keyword", "index": False},
                    "datasheet_url": {"type": "keyword", "index": False},
                }
            }
        }
        self._client.indices.create(index=self.es_index, **mapping)

    # Args:
    #   None
    # Returns:
    #   None
    # Notes:
    #   Bulk loads fallback docs into Elasticsearch only when index is empty.
    def _seed_if_empty(self) -> None:
        assert self._client is not None
        count = self._client.count(index=self.es_index)["count"]
        if count > 0:
            return

        actions = []
        for doc in self._fallback_docs:
            doc_copy = dict(doc)
            doc_copy["spec_blob"] = _spec_blob_from_doc(doc_copy)
            actions.append({"_index": self.es_index, "_id": doc_copy["id"], "_source": doc_copy})

        if actions:
            helpers.bulk(self._client, actions)

    # Args:
    #   intent: QueryIntent
    #     Structured query and constraint payload.
    # Returns:
    #   list[ProductResult]
    #     Ranked search results from Elasticsearch.
    # Notes:
    #   Ranking blends ES relevance with stock/price/coverage scoring.
    def _search_elasticsearch(self, intent: QueryIntent) -> list[ProductResult]:
        assert self._client is not None

        must = [
            {
                "multi_match": {
                    "query": intent.keywords,
                    "fields": [
                        "name^4",
                        "description^3",
                        "category^2",
                        "manufacturer^2",
                        "tags^2",
                        "use_cases^2",
                        "spec_blob",
                    ],
                    "fuzziness": "AUTO",
                }
            }
        ]

        filters: list[dict[str, Any]] = []
        if intent.in_stock_only:
            filters.append({"range": {"quantity_available": {"gt": 0}}})
        if intent.min_quantity is not None:
            filters.append({"range": {"quantity_available": {"gte": intent.min_quantity}}})
        if intent.max_unit_price is not None:
            filters.append({"range": {"unit_price": {"lte": intent.max_unit_price}}})

        sort: list[Any] = ["_score"]
        if intent.sort_preference == "price_low":
            sort = [{"unit_price": "asc"}, "_score"]
        elif intent.sort_preference == "stock_high":
            sort = [{"quantity_available": "desc"}, "_score"]

        response = self._client.search(
            index=self.es_index,
            query={"bool": {"must": must, "filter": filters}},
            size=intent.limit,
            sort=sort,
        )

        hits = response.get("hits", {}).get("hits", [])
        if not hits:
            return []

        top_score = max((hit.get("_score") or 1.0) for hit in hits)
        results: list[ProductResult] = []

        for hit in hits:
            doc = hit.get("_source", {})
            score = float(hit.get("_score") or 0.0)
            coverage = _keyword_coverage(intent.keywords, doc)
            recommendation_score = _recommendation_score(score, top_score, doc, coverage)
            reason = _build_reason(doc, recommendation_score, coverage)
            results.append(
                ProductResult(
                    id=doc["id"],
                    manufacturer=doc["manufacturer"],
                    manufacturer_part_number=doc["manufacturer_part_number"],
                    name=doc["name"],
                    description=doc["description"],
                    category=doc["category"],
                    unit_price=float(doc["unit_price"]),
                    quantity_available=int(doc["quantity_available"]),
                    product_url=doc["product_url"],
                    datasheet_url=doc["datasheet_url"],
                    recommendation_score=recommendation_score,
                    fit_reason=reason,
                )
            )

        results.sort(key=lambda r: r.recommendation_score, reverse=True)
        return results

    # Args:
    #   intent: QueryIntent
    #     Structured query and constraints.
    # Returns:
    #   list[ProductResult]
    #     Ranked fallback results from local JSON catalog.
    # Notes:
    #   Provides resiliency when Elasticsearch is unavailable.
    def _fallback_search(self, intent: QueryIntent) -> list[ProductResult]:
        stop_words = {
            "find",
            "need",
            "with",
            "that",
            "this",
            "for",
            "the",
            "and",
            "top",
            "best",
            "under",
            "cheapest",
            "stock",
            "in-stock",
        }
        query_tokens = {
            token.strip(",.?!")
            for token in intent.keywords.lower().split()
            if len(token) > 2 and token.strip(",.?!") not in stop_words
        }
        results: list[ProductResult] = []

        for doc in self._fallback_docs:
            haystack = " ".join(
                [
                    doc["manufacturer"],
                    doc["manufacturer_part_number"],
                    doc["name"],
                    doc["description"],
                    " ".join(doc.get("tags", [])),
                    " ".join(doc.get("use_cases", [])),
                ]
            ).lower()

            match_score = sum(token in haystack for token in query_tokens)
            if query_tokens and match_score == 0:
                continue

            if intent.in_stock_only and doc["quantity_available"] <= 0:
                continue
            if intent.min_quantity is not None and doc["quantity_available"] < intent.min_quantity:
                continue
            if intent.max_unit_price is not None and doc["unit_price"] > intent.max_unit_price:
                continue

            coverage = _keyword_coverage(intent.keywords, doc)
            recommendation_score = _recommendation_score(1.0, 1.0, doc, coverage)
            results.append(
                ProductResult(
                    id=doc["id"],
                    manufacturer=doc["manufacturer"],
                    manufacturer_part_number=doc["manufacturer_part_number"],
                    name=doc["name"],
                    description=doc["description"],
                    category=doc["category"],
                    unit_price=float(doc["unit_price"]),
                    quantity_available=int(doc["quantity_available"]),
                    product_url=doc["product_url"],
                    datasheet_url=doc["datasheet_url"],
                    recommendation_score=recommendation_score,
                    fit_reason=_build_reason(doc, recommendation_score, coverage),
                )
            )

        results.sort(key=lambda r: r.recommendation_score, reverse=True)
        return results[: intent.limit]

    # Args:
    #   None
    # Returns:
    #   list[dict[str, Any]]
    #     Parsed product documents from seed catalog JSON.
    @staticmethod
    def _load_seed_catalog() -> list[dict[str, Any]]:
        catalog_path = Path(__file__).resolve().parent.parent / "data" / "catalog.json"
        with catalog_path.open("r", encoding="utf-8") as f:
            return json.load(f)


# Args:
#   doc: dict[str, Any]
#     Product document that may include key_specs.
# Returns:
#   str
#     Flattened key/spec string used by full-text search.
def _spec_blob_from_doc(doc: dict[str, Any]) -> str:
    specs = doc.get("key_specs", {})
    if not isinstance(specs, dict):
        return ""
    return " ".join(f"{key} {value}" for key, value in specs.items())


# Args:
#   raw_score: float
#     Elasticsearch score for the hit.
#   top_score: float
#     Best score in the current result set for normalization.
#   doc: dict[str, Any]
#     Product document used for stock and price features.
#   coverage: float
#     Keyword coverage ratio (0.0 to 1.0).
# Returns:
#   float
#     Composite recommendation score (higher is better).
def _recommendation_score(raw_score: float, top_score: float, doc: dict[str, Any], coverage: float) -> float:
    relevance = raw_score / max(top_score, 0.0001)
    stock = min(doc.get("quantity_available", 0) / 10000, 1.0)
    price = doc.get("unit_price", 0.0)
    price_score = 1 / (1 + max(price, 0.0))
    return round(
        (0.78 * relevance) + (0.15 * coverage) + (0.05 * stock) + (0.02 * price_score),
        4,
    )


# Args:
#   doc: dict[str, Any]
#     Product document.
#   recommendation_score: float
#     Final composite score used for ranking.
#   coverage: float
#     Keyword coverage ratio.
# Returns:
#   str
#     Human-readable explanation displayed in the UI.
def _build_reason(doc: dict[str, Any], recommendation_score: float, coverage: float) -> str:
    return (
        f"Score {recommendation_score:.2f} with keyword coverage {coverage:.2f}, "
        f"stock ({doc.get('quantity_available', 0)} pcs), and price (${doc.get('unit_price', 0):.2f})."
    )


# Args:
#   query: str
#     User query text.
#   doc: dict[str, Any]
#     Product document to compare against query terms.
# Returns:
#   float
#     Fraction of significant query tokens found in document text fields.
def _keyword_coverage(query: str, doc: dict[str, Any]) -> float:
    stop_words = {
        "find",
        "need",
        "with",
        "that",
        "this",
        "for",
        "the",
        "and",
        "top",
        "best",
        "under",
        "in",
        "stock",
    }
    query_tokens = {
        token.strip(",.?!")
        for token in query.lower().split()
        if len(token) > 2 and token.strip(",.?!") not in stop_words
    }
    if not query_tokens:
        return 0.0

    haystack = " ".join(
        [
            doc.get("manufacturer", ""),
            doc.get("manufacturer_part_number", ""),
            doc.get("name", ""),
            doc.get("description", ""),
            " ".join(doc.get("tags", [])),
            " ".join(doc.get("use_cases", [])),
        ]
    ).lower()

    matched = sum(token in haystack for token in query_tokens)
    return matched / len(query_tokens)
