# Phase 1 — Company Knowledge Architecture

## Goal

Build the initial SoraMinds Company Knowledge Base from the public website.

Phase 1 is deliberately synchronous:

```text
Seed URL
   ↓
URL Discovery
   ↓
Page / Section Extraction
   ↓
Normalization
   ↓
Structured LLM Extraction
   ↓
Repository
   ↓
SQLite
```

The scheduler, Celery workers, website-change events, Media Intelligence, and social publishing are later phases.

## Agreed technology choices

- Python 3.12+
- Playwright async API for browser rendering and DOM extraction
- Pydantic v2 for internal and structured-output models
- SQLite for initial persistence
- SQLAlchemy 2.x for database access
- Alembic for schema migrations
- Shared LLM provider registry under `app/core/llm`
- `asyncio` for bounded browser concurrency
- SHA-256 via `hashlib` for deterministic fingerprints where needed
- pytest / pytest-asyncio
- Ruff
- uv
- unicode-sanity for Unicode text cleanup behind an adapter

Not required in Phase 1:

- Celery
- Redis
- Kafka / RabbitMQ
- WebSockets
- Event bus
- Vector database
- Elasticsearch

## Folder structure

```text
app/
├── settings.py
│
├── core/
│   └── llm/
│       ├── base.py
│       ├── spec.py
│       ├── registry.py
│       └── providers/
│           └── openai.py
│
├── database/
│   ├── __init__.py
│   ├── connection.py
│   └── schema.py
│
├── repository/
│   ├── __init__.py
│   ├── base.py
│   └── operations/
│       ├── __init__.py
│       └── sqlite_operation.py
│
├── infrastructure/
│   └── browser/
│       ├── base.py
│       └── browser.py
│
└── modules/
    └── company_knowledge/
        ├── service.py
        ├── crawl/
        │   ├── base.py
        │   ├── bfs.py
        │   ├── link_extractor.py
        │   ├── preprocess_url.py
        │   └── validation.py
        ├── discovery/
        │   ├── base.py
        │   └── page_discovery.py
        ├── normalization/
        │   ├── base.py
        │   ├── normalize.py
        │   ├── text_cleaner.py
        │   └── text_utils.py
        ├── extraction/
        │   ├── base.py
        │   └── extractor.py
        └── models/
            ├── crawl.py
            ├── page.py
            └── knowledge.py
```

## Repository Pattern

The agreed persistence design is:

```text
CompanyKnowledgeService
          │
          ▼
    Repository Base
          │
          ▼
  SQLite Operation
          │
          ▼
      Database
```

### `app/repository/base.py`

Defines the persistence contract.

Conceptually:

```python
class Repository(ABC):
    @abstractmethod
    def save(self, data): ...

    @abstractmethod
    def get(self, id): ...

    @abstractmethod
    def update(self, id, data): ...

    @abstractmethod
    def delete(self, id): ...
```

### `app/repository/operations/sqlite_operation.py`

Contains the SQLite implementation of the repository contract.

Later another backend can be added:

```text
repository/
└── operations/
    ├── sqlite_operation.py
    └── postgres_operation.py
```

Company Knowledge should not contain SQLite-specific logic.

### `app/database/connection.py`

Responsible only for database connection/session setup.

### `app/database/schema.py`

Responsible for database schema/table definitions.

This separates:

```text
repository/
= how application data is persisted/retrieved

database/
= database connection + schema

company_knowledge/
= business/domain workflow
```

## 1. URL discovery

The crawler answers only:

> Which internal pages belong to the company website?

`CrawlStrategy` is a thin contract with one operation:

```python
async def discover(seed_url: str) -> CrawlResult
```

Current implementation:

- `BFSCrawlStrategy` — bounded breadth-first traversal
- `LinkExtractor` — strategy-independent contract for extracting links from one URL
- `BrowserLinkExtractor` — rendered-page implementation using the shared browser abstraction

Possible later implementations:

- `SitemapCrawlStrategy`
- `ManualURLStrategy`
- `HybridCrawlStrategy`

`preprocess_url.py` owns URL transformation only:

- relative URL → absolute URL
- remove the `#section` anchor
- normalize the ending slash

`validation.py` owns crawl validation:

- same company domain
- skip static assets

`app/settings.py` owns the shared `SKIPPED_EXTENSIONS` configuration used by crawl validation.

Current Phase 1 decisions:

- no tracking-parameter normalization
- no explicit HTTP/HTTPS-only validation
- PDF is not currently treated as a skipped static asset
- root URLs are normalized so `https://example.com` and `https://example.com/` are treated consistently
- deduplication belongs to the BFS crawl logic, not URL preprocessing

`BFSCrawlStrategy`:

- starts from the normalized seed URL at depth 0
- traverses URLs level by level to preserve BFS ordering
- depends on the `LinkExtractor` abstraction rather than Playwright/browser details
- preprocesses and validates links before queueing them
- builds canonical deduplication keys that treat `www.example.com` and `example.com` as the same host
- adds deduplication keys to the `seen` set when URLs are queued so duplicate discoveries are not queued twice
- enforces `max_pages` and `max_depth`
- uses a crawl-level `asyncio.Semaphore` so only the configured number of link-extraction tasks run at once
- uses `asyncio.gather(..., return_exceptions=True)` so one page failure does not abort the entire crawl
- records the seed URL in `CrawlResult.urls`
- counts successfully rendered pages in `visited_count`
- counts rejected duplicate/non-crawlable links and page failures in `skipped_count`

`BrowserLinkExtractor`:

- opens one browser page/tab per extraction
- navigates through the shared `BrowserBase`
- extracts rendered `a[href]` links
- closes the page in `finally`
- owns the `asyncio.Semaphore` that limits concurrent browser-page extraction

Browser lifecycle remains outside both the crawl strategy and link extractor. The caller starts and closes the shared browser so the same browser can also be reused by Page Discovery.

The separation keeps traversal independent from link extraction:

```text
BFSCrawlStrategy
      ↓
LinkExtractor
      ↑
BrowserLinkExtractor
      ↓
BrowserBase
```

A later crawl strategy such as a sitemap strategy does not need to depend on browser-based link extraction.

## Tests

The BFS crawler is covered by focused unit tests:

```text
tests/modules/company_knowledge/crawl/
├── test_bfs.py
├── test_link_extractor.py
└── test_validation.py
```

Coverage includes:

- breadth-first ordering
- duplicate URL handling
- `max_pages`
- `max_depth`
- per-page extraction failure handling
- invalid crawl limits
- browser link extraction and page cleanup
- bounded browser extraction concurrency
- bounded crawl-level concurrency
- deduplication across `www.` and non-`www.` host variants
- same-domain validation
- `www.` host normalization
- external URL rejection
- static asset filtering

## 2. Browser infrastructure

Playwright should be initialized once and shared.

```text
BFSCrawlStrategy ──> LinkExtractor
                         ↑
                 BrowserLinkExtractor ──> Browser interface ──> Playwright implementation

PageDiscovery ──────────────────────────> Browser interface
```

Use the async Playwright API. Do not launch a fresh browser process for every URL.

## 3. Page discovery

`page_discovery.py` uses the shared browser abstraction from `app/infrastructure/browser`.
It owns Company Knowledge-specific DOM extraction, while `browser.py` owns browser lifecycle/navigation.

```text
page_discovery.py
       ↓
browser/base.py
       ↓
browser/browser.py
       ↓
Playwright
```

Given one URL, return structural facts about the rendered page.

`PageDiscovery` receives the shared `BrowserBase`. For each extraction it opens a
page, navigates it, inspects the rendered DOM, and closes that page in `finally`.
The caller owns the browser lifecycle, so Page Discovery does not start or close
the shared browser.

Use outermost `<section>` elements as the page boundary. Prefer outermost
sections below `<main>` when a main element exists; otherwise, fall back to
outermost sections across the document. Preserve DOM order and empty sections.

Extract:

- current/final URL after navigation
- title
- meta description
- canonical URL
- section position
- DOM id/classes as metadata
- h1–h6 heading text and level
- full section text
- direct child count

Missing or empty page metadata becomes `None`; section and heading text remains
as observed. Page Discovery performs factual DOM extraction only. It does not
infer semantics, normalize text, persist data, or invoke an LLM.

## 4. Models

### `models/crawl.py`

Crawl metadata such as URL, depth, discovered-from, visited count, and skipped count.

### `models/page.py`

Observed page structure:

- Heading
- PageSection
- PageDocument

### `models/knowledge.py`

Semantic extraction output:

- SectionKnowledge
- PageKnowledge

```text
PageDocument
= what Playwright observed

PageKnowledge
= what the extraction layer understood
```

## 5. Normalization

Normalization is deterministic, synchronous, and conservative.

`NormalizerBase` is a thin abstraction that defines only the `normalize(page)` contract. `PageNormalizer` owns the page-specific cleaning implementation and receives `TextCleaner` through constructor injection.

The normalization pipeline includes:

- `TextCleaner` — application-facing contract for Unicode cleanup
- `UnicodeSanityAdapter` — adapts the third-party `unicode-sanity` package to the `TextCleaner` contract
- `PageNormalizer.clean_text()` — uses the injected cleaner, then normalizes whitespace
- `PageNormalizer.clean_heading()` — cleans heading text while preserving heading level
- `PageNormalizer.clean_section()` — cleans section text/headings while preserving DOM metadata
- `text_utils.clean_unwanted_space()` — pure whitespace cleanup
- `text_utils.remove_empty_sections()` — pure empty-section filtering

The adapter keeps `unicode-sanity` out of `normalize.py` so the normalization logic depends on our own `TextCleaner` contract rather than a specific third-party library.

`PageNormalizer` requires a `TextCleaner` to be passed explicitly and stores it once. `NormalizerBase` stays independent of text-cleaning implementation details.

`normalize.py` owns the page-specific normalization behavior. `NormalizerBase` remains contract-only, while `text_utils.py` contains cleaner-independent pure helpers.

```text
caller / composition layer
          ↓
UnicodeSanityAdapter
          ↓
PageNormalizer(TextCleaner)
          ↓
NormalizerBase contract
          ↓
text_utils.py
```

`PageNormalizer.normalize()` cleans:

- page title
- meta description
- section headings
- section text
- empty sections

It does not modify page URLs, canonical URLs, section IDs/classes, child counts, or add semantic interpretation.

Normalization stays synchronous because it performs only local Python data/string cleanup and does not use browser, network, database, or LLM calls.

## 6. LLM extraction

The extraction layer receives normalized page/section models and returns structured knowledge.

Possible output:

- page summary
- section summary
- semantic label
- topics
- entities
- knowledge items
- optional atomic facts

LLM access goes through:

```text
KnowledgeExtractor
       ↓
core.llm.registry
       ↓
configured provider
```

The Company Knowledge module must not branch directly on provider names.

## 7. Service orchestration

`service.py` coordinates the Phase 1 flow:

```python
urls = crawler.discover(seed_url)

for url in urls:
    page = discovery.extract(url)
    normalized = normalizer.normalize(page)
    knowledge = extractor.extract(normalized)
    repository.save(normalized, knowledge)
```

The service must not contain:

- raw Playwright implementation details
- provider-specific LLM SDK logic
- raw SQLite statements

## Documentation sync rule

Whenever the folder structure, architecture, responsibilities, or any decision documented here changes, update this document in the same PR so the documentation matches the code.

## Final Phase 1 decisions

1. Use `modules/` as the bounded application-module root.
2. Keep Phase 1 synchronous and explicit.
3. Use Strategy Pattern for crawl discovery.
4. Use async Playwright.
5. Share browser lifecycle infrastructure.
6. Keep DOM discovery factual; keep semantic interpretation in extraction.
7. Use a shared Repository Pattern under `app/repository`.
8. Keep DB connection/schema under `app/database`.
9. Keep SQLite implementation under `repository/operations/sqlite_operation.py`.
10. Do not use JSON files as the source of truth.
11. Do not introduce Celery/events in Phase 1.
12. Do not hardcode business semantics from CSS classes or section positions.
