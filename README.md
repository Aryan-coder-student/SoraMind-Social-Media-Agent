# SoraMind Social Media Agent

Phase 1 scaffolds the **Company Knowledge** pipeline.

The initial implementation is intentionally synchronous and focuses on:

1. URL discovery
2. Page/section extraction
3. Normalization
4. Structured LLM extraction
5. Persistence

See [docs/phase-1-architecture.md](docs/phase-1-architecture.md) for the agreed architecture, responsibilities, and technology decisions.

## Run the persisted Company Knowledge pipeline

Use the browser-backed command to crawl rendered pages, normalize and
fingerprint their content, and persist immutable versions to SQLite:

```bash
python -m app.company_knowledge_cli build https://www.soraminds.com/ \
  --database-url sqlite:///./soramind.db \
  --max-pages 10 \
  --max-depth 2 \
  --concurrency 5
```

`build` safely processes useful partial results and never deactivates URLs that
were not discovered. When the configured limits cover the complete reachable
site, run the explicit complete-crawl operation:

```bash
python -m app.company_knowledge_cli \
  build-and-deactivate-missing-pages \
  https://www.soraminds.com/ \
  --database-url sqlite:///./soramind.db \
  --max-pages 100 \
  --max-depth 5
```

The complete-crawl operation exits with `IncompleteCrawlError` before changing
page state when a page or depth limit is reached or link extraction fails.

## Run with Docker

The current runnable component discovers internal URLs with the Phase 1 crawler.

```bash
SEED_URL=https://example.com docker compose up --build
```

The crawl defaults to 10 pages, depth 1, and concurrency 5. Override those
limits when needed:

```bash
SEED_URL=https://example.com MAX_PAGES=50 MAX_DEPTH=3 CONCURRENCY=8 docker compose up --build
```

You can also build and run the image directly:

```bash
docker build -t soramind-agent .
docker run --rm --init --ipc=host soramind-agent https://example.com --max-pages 10 --max-depth 1
```
