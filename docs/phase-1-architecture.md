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
Persistence
```

The scheduler, Celery workers, website-change events, Media Intelligence, and social publishing are later phases.

## Agreed technology choices

- Python 3.12+
- Playwright async API for browser rendering and DOM extraction
- Pydantic v2 for internal and structured-output models
- SQLite for the initial persistence layer
- SQLAlchemy 2.x for database access
- Alembic for schema migrations
- Shared LLM provider registry under `app/core/llm`
- `asyncio` for bounded browser concurrency
- SHA-256 via `hashlib` for deterministic fingerprints where needed
- pytest / pytest-asyncio for tests
- Ruff for linting and formatting
- uv for dependency/environment management

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
├── core/
│   └── llm/
│       ├── base.py
│       ├── spec.py
│       ├── registry.py
│       └── providers/
│           └── openai.py
│
├── infrastructure/
│   ├── browser/
│   │   ├── base.py
│   │   └── playwright.py
│   │
│   └── persistence/
│       └── sqlite/
│           ├── connection.py
│           ├── schema.py
│           └── repositories/
│               └── company_knowledge.py
│
└── modules/
    └── company_knowledge/
        ├── service.py
        ├── crawl/
        │   ├── base.py
        │   ├── bfs.py
        │   └── preprocess_url.py
        ├── discovery/
        │   ├── base.py
        │   └── playwright.py
        ├── normalization/
        │   ├── base.py
        │   └── normalize.py
        ├── extraction/
        │   ├── base.py
        │   └── extractor.py
        ├── models/
        │   ├── crawl.py
        │   ├── page.py
        │   └── knowledge.py
        └── repository/
            └── base.py
```

## Dependency direction

```text
CompanyKnowledgeService
        │
        ├── CrawlStrategy
        ├── PageDiscovery
        ├── PageNormalizer
        ├── KnowledgeExtractor
        │       └── LLMProvider
        └── CompanyKnowledgeRepository
                ▲
                │
        SQLite implementation
```

Domain code depends on interfaces. Concrete browser, LLM provider, and database implementations remain outside the Company Knowledge domain.

## 1. URL discovery

### Responsibility

Answer only:

> Which internal pages belong to the company website?

The crawler must not call the LLM or persist company knowledge.

### Pattern

`CrawlStrategy` is the abstraction.

Current implementation:

- `BFSCrawlStrategy`

Possible later implementations:

- `SitemapCrawlStrategy`
- `ManualURLStrategy`
- `HybridCrawlStrategy`

### URL preprocessing

`preprocess_url.py` owns deterministic URL cleanup:

- convert relative URLs to absolute
- allow only configured domains
- remove fragments
- remove known tracking parameters
- normalize trailing slashes
- reject unsupported schemes
- skip static assets
- deduplicate canonical crawl URLs

Do not remove all query parameters blindly; some may carry meaningful application state.

### Crawl safety

BFS should be bounded by configuration such as:

- max pages
- max depth
- allowed domains
- navigation timeout
- bounded concurrency

## 2. Browser infrastructure

Playwright should be initialized once and shared.

Avoid launching a new browser process for each URL.

```text
BFSCrawlStrategy ──┐
                   ├── Browser interface ──> Playwright implementation
PageDiscovery ─────┘
```

Use the async Playwright API so later page acquisition can use controlled concurrency.

## 3. Page discovery

### Responsibility

Given one URL, return structural facts about the rendered page.

For SoraMinds, the primary structural boundary is the outermost `<section>` elements under the page's main content.

Extract facts such as:

- URL
- title
- meta description
- canonical URL
- section position
- section DOM id/classes as metadata
- all h1–h6 headings with level/text
- full section text
- links
- images
- child count

Do not infer products, pricing, features, or other semantics from CSS classes or section positions.

Some valid sections have no heading, so heading presence cannot be the only section rule.

## 4. Models

### `models/crawl.py`

Represents crawl results and crawl metadata.

Examples:

- discovered URL
- crawl depth
- discovered-from URL
- visited/skipped counts

### `models/page.py`

Represents what the browser observed.

Suggested concepts:

- Heading
- PageLink
- PageImage
- PageSection
- PageDocument

### `models/knowledge.py`

Represents what the semantic extraction layer understood.

Suggested concepts:

- KnowledgeItem
- Entity
- optional Fact
- SectionKnowledge
- PageKnowledge

Important distinction:

```text
PageDocument
= observed website structure

PageKnowledge
= semantic interpretation
```

## 5. Normalization

Normalization is deterministic and conservative.

Examples:

- normalize whitespace
- normalize repeated newlines
- canonicalize URLs where appropriate
- remove empty sections
- remove obvious presentation-only noise

Normalization must not introduce semantic labels or business interpretation.

## 6. LLM extraction

The extraction layer receives normalized page/section models and returns structured knowledge.

Possible outputs:

- page summary
- section summary
- semantic label
- topics
- entities
- knowledge items
- optional atomic facts

LLM providers are accessed through the shared registry:

```text
KnowledgeExtractor
       ↓
core.llm.registry
       ↓
configured provider
```

The Company Knowledge module must not branch directly on provider names.

## 7. Persistence boundary

The repository interface belongs to the Company Knowledge domain:

```text
modules/company_knowledge/repository/base.py
```

The SQLite implementation belongs to infrastructure:

```text
infrastructure/persistence/sqlite/repositories/company_knowledge.py
```

This keeps Company Knowledge independent from SQLite and allows a later PostgreSQL implementation without changing domain logic.

## 8. Service orchestration

`service.py` coordinates the Phase 1 pipeline.

Conceptually:

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
- provider-specific LLM SDK code
- raw SQLite statements

## Design decisions

1. Use `modules/` as the application boundary; do not use a top-level `generation/` package for Company Knowledge.
2. Keep Phase 1 synchronous and explicit.
3. Use Strategy Pattern for crawl discovery.
4. Share browser infrastructure between crawling and page extraction.
5. Use async Playwright.
6. Keep DOM discovery factual and semantic interpretation in the LLM extraction layer.
7. Keep repository interfaces in the domain and concrete persistence implementations in infrastructure.
8. Do not use JSON files as the source of truth for discovered URLs.
9. Do not introduce Celery/events until the ongoing website-update phase.
10. Do not hardcode SoraMinds products/services from CSS classes or section indexes.
