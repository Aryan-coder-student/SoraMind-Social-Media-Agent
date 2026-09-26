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
        │   ├── preprocess_url.py
        │   └── validation.py
        ├── discovery/
        │   ├── base.py
        │   └── page_discovery.py
        ├── normalization/
        │   ├── base.py
        │   └── normalize.py
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

`CrawlStrategy` is the abstraction.

Current implementation:

- `BFSCrawlStrategy`

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
- deduplication belongs to the BFS crawl logic, not URL preprocessing

BFS must have safety limits such as max pages, max depth, timeout, and bounded concurrency.

## 2. Browser infrastructure

Playwright should be initialized once and shared.

```text
BFSCrawlStrategy ──┐
                   ├── Browser interface ──> Playwright implementation
PageDiscovery ─────┘
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

For SoraMinds, use outermost `<section>` elements as the primary page boundary.

Extract:

- URL
- title
- meta description
- canonical URL
- section position
- DOM id/classes as metadata
- h1–h6 headings
- full section text
- links
- images
- child count

Do not infer products, pricing, features, or services from CSS classes or positions.

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

Normalization is deterministic and conservative:

- whitespace cleanup
- newline normalization
- URL normalization where appropriate
- empty-section removal
- obvious presentation-noise removal

It must not add semantic interpretation.

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
