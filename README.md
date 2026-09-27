# SoraMind Social Media Agent

Phase 1 scaffolds the **Company Knowledge** pipeline.

The initial implementation is intentionally synchronous and focuses on:

1. URL discovery
2. Page/section extraction
3. Normalization
4. Structured LLM extraction
5. Persistence

See [docs/phase-1-architecture.md](docs/phase-1-architecture.md) for the agreed architecture, responsibilities, and technology decisions.

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


## Run the SoraMinds crawl snapshot

The repository also includes a manual runner for the current pre-LLM pipeline:

```bash
python run_soraminds_crawl.py
```

It defaults to:

```text
https://www.soraminds.com/
```

and writes:

```text
soraminds_crawl_output.json
```

The JSON contains:

- crawl metadata and discovered URLs
- raw PageDocument output for each discovered page
- normalized PageDocument output
- per-page extraction errors, without aborting the whole snapshot

Useful overrides:

```bash
python run_soraminds_crawl.py \
  --max-pages 25 \
  --max-depth 2 \
  --concurrency 5 \
  --output output/soraminds_crawl.json
```

Use `--headed` to show Chromium while the crawl runs.
