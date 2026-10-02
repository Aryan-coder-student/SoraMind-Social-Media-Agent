# SoraMind Social Media Agent

Phase 1 scaffolds the **Company Knowledge** pipeline.

The initial implementation is intentionally synchronous and focuses on:

1. URL discovery
2. Page/section extraction
3. Normalization
4. Deterministic fingerprinting and change detection
5. Versioned persistence
6. Optional LLM summaries of changed sections

See [docs/phase-1-architecture.md](docs/phase-1-architecture.md) for the implemented Company Knowledge architecture.

Phase 2 autonomous content planning and publishing is designed in [docs/phase-2-architecture.md](docs/phase-2-architecture.md).

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
