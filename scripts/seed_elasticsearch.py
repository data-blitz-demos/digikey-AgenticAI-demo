from __future__ import annotations

"""
Property of Data-Blitz Inc.
Author: Paul Harvener

Seeder script that prepares Elasticsearch index mapping and loads mock catalog data.
"""

import json
import os
import time
from pathlib import Path

from elasticsearch import Elasticsearch, helpers


MAPPING = {
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


# Args:
#   None
# Returns:
#   None
# Notes:
#   Creates or refreshes the target index and bulk-loads catalog documents.
def main() -> None:
    es_url = os.getenv("ELASTICSEARCH_URL", "http://elasticsearch:9200")
    index_name = os.getenv("ELASTICSEARCH_INDEX", "digikey_products")
    username = os.getenv("ELASTICSEARCH_USERNAME") or None
    password = os.getenv("ELASTICSEARCH_PASSWORD") or None
    recreate = os.getenv("ELASTICSEARCH_SEED_RECREATE", "false").lower() == "true"

    auth = (username, password) if username and password else None
    client = Elasticsearch(es_url, basic_auth=auth, request_timeout=20)

    wait_for_elasticsearch(client)
    wait_for_query_ready(client)

    if recreate and call_with_retries(lambda: client.indices.exists(index=index_name)):
        print(f"Deleting existing index: {index_name}")
        call_with_retries(lambda: client.indices.delete(index=index_name))

    if not call_with_retries(lambda: client.indices.exists(index=index_name)):
        print(f"Creating index: {index_name}")
        call_with_retries(lambda: client.indices.create(index=index_name, **MAPPING))

    existing = call_with_retries(lambda: client.count(index=index_name)).get("count", 0)
    if existing > 0 and not recreate:
        print(f"Index already has {existing} docs. Skipping seed.")
        return

    docs = load_catalog_docs()
    actions = []
    for doc in docs:
        source = dict(doc)
        source["spec_blob"] = spec_blob(source)
        actions.append({"_index": index_name, "_id": source["id"], "_source": source})

    if actions:
        call_with_retries(lambda: helpers.bulk(client, actions))

    call_with_retries(lambda: client.indices.refresh(index=index_name))
    final_count = call_with_retries(lambda: client.count(index=index_name)).get("count", 0)
    print(f"Seed complete. Indexed {final_count} documents into {index_name}.")


# Args:
#   client: Elasticsearch
#     Initialized Elasticsearch client.
#   attempts: int
#     Maximum ping attempts.
#   sleep_seconds: float
#     Delay between attempts.
# Returns:
#   None
# Raises:
#   RuntimeError
#     If Elasticsearch cannot be reached after retries.
def wait_for_elasticsearch(client: Elasticsearch, attempts: int = 60, sleep_seconds: float = 2.0) -> None:
    for attempt in range(1, attempts + 1):
        try:
            if client.ping():
                print("Elasticsearch is reachable.")
                return
        except Exception:
            pass
        print(f"Waiting for Elasticsearch... ({attempt}/{attempts})")
        time.sleep(sleep_seconds)

    raise RuntimeError("Elasticsearch did not become available in time")


# Args:
#   client: Elasticsearch
#     Initialized Elasticsearch client.
#   attempts: int
#     Maximum readiness attempts.
#   sleep_seconds: float
#     Delay between attempts.
# Returns:
#   None
# Raises:
#   RuntimeError
#     If cluster/query APIs do not become ready after retries.
def wait_for_query_ready(client: Elasticsearch, attempts: int = 30, sleep_seconds: float = 2.0) -> None:
    for attempt in range(1, attempts + 1):
        try:
            client.cluster.health(wait_for_status="yellow", timeout="30s")
            client.info()
            print("Elasticsearch query APIs are ready.")
            return
        except Exception:
            pass
        print(f"Waiting for Elasticsearch query readiness... ({attempt}/{attempts})")
        time.sleep(sleep_seconds)

    raise RuntimeError("Elasticsearch query APIs did not become ready in time")


# Args:
#   func: callable
#     Operation to execute against Elasticsearch.
#   attempts: int
#     Maximum retry attempts.
#   sleep_seconds: float
#     Delay between attempts.
# Returns:
#   Any
#     Return value from the callable upon success.
# Raises:
#   Exception
#     Re-raises the last encountered exception after exhausting retries.
def call_with_retries(func, attempts: int = 20, sleep_seconds: float = 1.5):
    last_exc = None
    for attempt in range(1, attempts + 1):
        try:
            return func()
        except Exception as exc:
            last_exc = exc
            print(f"Retrying after transient Elasticsearch error ({attempt}/{attempts}): {exc}")
            time.sleep(sleep_seconds)
    if last_exc:
        raise last_exc
    raise RuntimeError("Retry operation failed unexpectedly")


# Args:
#   None
# Returns:
#   list[dict]
#     Product documents loaded from data/catalog.json.
def load_catalog_docs() -> list[dict]:
    catalog_path = Path(__file__).resolve().parent.parent / "data" / "catalog.json"
    with catalog_path.open("r", encoding="utf-8") as f:
        return json.load(f)


# Args:
#   doc: dict
#     Catalog document that may include key_specs.
# Returns:
#   str
#     Flattened searchable key-spec string.
def spec_blob(doc: dict) -> str:
    specs = doc.get("key_specs", {})
    if not isinstance(specs, dict):
        return ""
    return " ".join(f"{key} {value}" for key, value in specs.items())


if __name__ == "__main__":
    main()
