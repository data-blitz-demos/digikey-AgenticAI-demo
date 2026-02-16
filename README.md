# DigiKey Generative AI Demo (Elasticsearch + Kibana + Docker Compose)

Property of Data-Blitz Inc.  
Author: Paul Harvener

This demo provides an AI assistant for DigiKey-style component discovery:
- Customers ask in natural language.
- The assistant extracts intent.
- Elasticsearch returns ranked mock catalog matches.
- Kibana is available for catalog exploration and debugging.

## Stack

- FastAPI app (chat API + web UI)
- Elasticsearch 8.11.4 (product catalog)
- Kibana 8.11.4 (catalog inspection)
- OpenAI API (optional) with default model target `gpt-5.2`

## Services in `docker-compose`

- `elasticsearch`: single-node cluster on `http://localhost:9200`
- `catalog-seeder`: one-shot service that creates/migrates index and bulk-loads `/data/catalog.json`
- `kibana`: on `http://localhost:5601`
- `app`: demo UI + API on `http://localhost:8000`

Startup order is enforced:
1. Elasticsearch becomes healthy.
2. Catalog seeder completes successfully.
3. App starts.

## Quick start

1. Create local env file:

```bash
cp .env.example .env
```

2. Boot everything:

```bash
docker compose up --build
```

3. Open:
- App UI: [http://localhost:8000](http://localhost:8000)
- Kibana: [http://localhost:5601](http://localhost:5601)

## Verify mock data loaded

```bash
curl -s http://localhost:9200/digikey_products/_count
```

Expected: non-zero document count.

## Kibana setup (first time)

1. Open Kibana at `http://localhost:5601`.
2. Go to `Stack Management -> Data Views`.
3. Create data view: `digikey_products*`.
4. Go to `Discover` and inspect catalog documents.

## LLM configuration

`OPENAI_API_KEY` is optional.
- If set, the app uses OpenAI Responses API for intent extraction.
- Default model target is `gpt-5.2` (`OPENAI_MODEL`).

If no key is set, a deterministic rules parser is used.

## Useful commands

Recreate index from scratch with mock data:

```bash
ELASTICSEARCH_SEED_RECREATE=true docker compose up --build
```

Bring stack down:

```bash
docker compose down
```

Remove volumes too (full reset):

```bash
docker compose down -v
```
