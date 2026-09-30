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
Fingerprinting
   ↓
Repository
   ↓
Configured database backend
(SQLite in Phase 1)
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
│           ├── openai.py
│           ├── anthropic.py
│           └── groq.py
│
├── database/
│   ├── __init__.py
│   ├── base.py
│   ├── connections/
│   │   ├── __init__.py
│   │   └── sqlite.py
│   └── schemas/
│       ├── __init__.py
│       ├── base.py
│       ├── page.py
│       ├── version.py
│       └── sqlalchemy.py
│
├── repository/
│   ├── __init__.py
│   ├── base.py
│   └── operations/
│       ├── __init__.py
│       ├── sqlalchemy.py
│       └── utils.py
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
        ├── fingerprint/
        │   ├── base.py
        │   └── sha256.py
        ├── extraction/
        │   ├── base.py
        │   └── extractor.py
        └── models/
            ├── crawl.py
            ├── knowledge.py
            ├── page.py
            └── version.py
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
 SQLAlchemyRepository
          │
          ▼
 SQLAlchemy session
          │
          ▼
 DatabaseConnection
          │
     ┌────┼──────────┐
     ▼    ▼          ▼
   SQLite PostgreSQL MongoDB
   (now)   (later)    (later)
```

### `app/repository/base.py`

Defines the persistence contract.

The Company Knowledge repository contract exposes current-state, immutable
history, and crawl-completion lifecycle operations:

```python
class Repository(ABC):
    @abstractmethod
    def save_page(
        self,
        page,
        page_fingerprint,
        section_fingerprints,
    ): ...

    @abstractmethod
    def get_page(self, url): ...

    @abstractmethod
    def get_page_fingerprint(self, url): ...

    @abstractmethod
    def delete_page(self, url): ...

    @abstractmethod
    def get_page_versions(self, url): ...

    @abstractmethod
    def get_page_version(self, url, version_number): ...

    @abstractmethod
    def get_latest_version(self, url): ...

    @abstractmethod
    def mark_missing_pages_inactive(self, seen_urls): ...
```

### `app/repository/operations/sqlalchemy.py`

Contains the relational repository implementation. It receives a SQLAlchemy
session factory and delegates domain ↔ persistence conversion to
`app/repository/operations/utils.py`.

`app/repository/operations/utils.py` contains mapping helpers between factual
domain models (`PageDocument` / `PageSection`) and immutable version rows
(`PageVersionRow` / `SectionVersionRow`). It also owns the URL boundary helper
that validates repository URL inputs as Pydantic `HttpUrl` values before
converting them to the SQL string representation.

`save_page()` is keyed by page URL and returns `NEW`, `UNCHANGED`, `CHANGED`,
or `REACTIVATED` with the latest version number:

```text
new URL
→ insert stable page identity
→ create immutable version 1
→ point pages.current_version_id at version 1

existing URL
→ load pages.current_version_id
→ compare the current version fingerprint
→ same fingerprint: keep the same immutable version
→ changed fingerprint: append the next version
→ move pages.current_version_id to the new version
```

The changed-page version insert and `current_version_id` pointer update use one
database transaction. Any failure rolls back both operations.

This operation layer is intentionally SQLAlchemy-specific rather than
SQLite-specific, so the same repository can be reused with a PostgreSQL
SQLAlchemy connection later. A document database can add a separate repository
implementation such as `mongodb.py`.

Company Knowledge does not import SQLAlchemy rows, sessions, or SQLite details.
Repository lookup/delete methods accept validated `HttpUrl` domain values; the
relational database still stores URLs as `TEXT`, because URL validation belongs
at the application/domain boundary rather than in a database-specific column type.

### `app/database/base.py`

Defines the backend-neutral database lifecycle contract. Application/domain code
depends on this boundary instead of importing a concrete database client.

The common contract contains only lifecycle behavior that applies across
relational and document databases:

```text
DatabaseConnection
├── connect()
└── close()
```

It intentionally does not define SQLAlchemy sessions, SQL statements, tables, or
MongoDB collections.

### `app/database/connections/sqlite.py`

Contains the Phase 1 SQLite backend. It owns SQLite-specific SQLAlchemy engine
configuration, session-factory creation, table creation, foreign-key enforcement,
and connection-pool setup. File-backed SQLite uses a small SQLAlchemy
`QueuePool` so repeated repository/session work can reuse checked-in
connections instead of reopening them. In-memory SQLite continues to use
`StaticPool` because an in-memory database belongs to one DB-API connection.

Pool size, overflow, and checkout timeout are configured in `app/settings.py`
through `SQLALCHEMY_POOL_SIZE`, `SQLALCHEMY_MAX_OVERFLOW`, and
`SQLALCHEMY_POOL_TIMEOUT`. The pool is intentionally small because SQLite
still serializes writes; pooling reduces connection setup overhead but does not
turn SQLite into a high-concurrency write database.

Future backends can be added without changing Company Knowledge:

```text
database/connections/
├── sqlite.py       ← Phase 1
├── postgres.py     ← later
└── mongodb.py      ← later
```

### `app/database/schemas/`

SQLAlchemy schema definitions are split by responsibility instead of keeping all
ORM models in one file:

- `base.py` defines the shared declarative `Base`.
- `page.py` defines stable page identity/lifecycle storage (`PageRow`).
- `version.py` defines immutable page/section version storage
  (`PageVersionRow` / `SectionVersionRow`).
- `sqlalchemy.py` remains a small compatibility export module so existing
  imports do not need to break immediately.

These mappings remain SQLAlchemy-specific rather than SQLite-specific, so the
relational model can be reused by another SQLAlchemy backend such as PostgreSQL.

- `pages.url` is the stable unique page identity.
- `pages.is_active` identifies URLs present in the latest completed crawl.
- `pages.current_version_id` points to the immutable version currently exposed
  as the page's current Company Knowledge state.
- `page_versions` stores all page content and page fingerprints with a per-page
  version number and timezone-aware UTC capture time.
- `section_versions` stores the complete ordered section snapshot for one page
  version.
- Current page content is not duplicated in `pages` or a separate current
  `sections` table.
- Fingerprint and foreign-key columns are indexed for later comparison and
  repository queries.

```text
pages
  │
  ├── current_version_id ─────────────┐
  │                                   ▼
  └──── 1 ─── * page_versions 1 ─── * section_versions
```

MongoDB would use its own document/collection representation rather than being
forced through the SQLAlchemy schema.

`pages` owns identity and lifecycle only. `page_versions` and
`section_versions` are the single source of truth for both current content and
historical content.

### Version creation

```text
Normalized PageDocument
        ↓
Repository
        ↓
compare page fingerprint
        ↓
changed fingerprint
        ↓
page_versions
        ↓
section_versions
```

Version numbering starts at 1 and increments independently for each page. A
snapshot is created only when the page fingerprint changes. The repository
always snapshots the complete normalized section set, which preserves added,
removed, and changed sections across versions. An identical fingerprint never
creates another version.

Canonical URL and DOM-only metadata are excluded from the content fingerprint.
When only those values change, the repository keeps the existing immutable
current version. Those metadata-only observations are not persisted as a new
content version in Phase 1.

### Removed and reappearing pages

Crawler traversal remains outside the repository. After a crawl completes, its
caller passes the set of seen validated URLs to
`mark_missing_pages_inactive()`:

```text
completed crawl URL set
        ↓
compare with active stored pages
        ↓
missing URL
        ↓
pages.is_active = false
```

Missing pages are soft-deactivated. Their page identity, current-version pointer,
and historical versions remain stored, and already inactive pages are not changed
repeatedly. Saving a previously inactive URL marks it active again and resumes
normal fingerprint comparison; an unchanged reappearance reuses the same current
version instead of creating a duplicate.

This separates:

```text
repository/
= how application data is persisted/retrieved

database/
= backend-neutral lifecycle + backend connections + persistence schemas

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
sections below `<main>` when a main element exists. If `<main>` contains no
sections, represent the main element as one factual section so client-rendered
page content is not lost. If `<main>` does not exist, fall back to outermost
sections across the document. Preserve DOM order and empty sections.

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

## 6. Fingerprinting

Fingerprinting runs after normalization and hashes exactly the normalized
content it receives:

```text
Normalized PageDocument
        ↓
Section fingerprints
        ↓
Page fingerprint
        ↓
Repository version comparison
```

`fingerprint_section()` and `fingerprint_page()` use canonical JSON serialized
as UTF-8 and SHA-256 hexadecimal digests. A section fingerprint contains ordered
heading levels and text plus the section text. It ignores section index, DOM id,
CSS classes, and direct child count so presentation-only changes do not change
the content hash.

A page fingerprint contains the title, meta description, and ordered section
fingerprints. It ignores page and canonical URLs because repository context owns
page identity. Section order remains significant.

Fingerprinting does not repeat normalization or use an LLM. The repository uses
the fingerprint for deterministic version creation. Semantic diffs and change
interpretation remain later responsibilities.

## 7. Optional LLM change interpretation

LLMs are not required for primary factual ingestion or fingerprint generation.
Later change-intelligence work may send only changed pages or sections for
semantic interpretation.

The shared provider layer is separate from Company Knowledge extraction:

```text
LLM consumer
     ↓
LLMRegistry
     ↓
ProviderSpec
     ↓
LLMProvider
     ├── OpenAIProvider
     ├── AnthropicProvider
     └── GroqProvider
```

`LLMProvider` exposes only asynchronous plain-text generation with an optional
system prompt. `ProviderSpec` records the provider factory, configurable default
model, and API-key environment variable name. `LLMRegistry` registers specs and
constructs providers through those factories without provider-specific branches.

A provider name identifies the API vendor (`openai`, `anthropic`, or `groq`). A
model is a configurable identifier passed to that vendor. Domain modules do not
branch on provider names, and SDK request/response types remain inside the
provider adapters.

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
Changed page / section
       ↓
Change interpreter
       ↓
core.llm.registry
       ↓
configured provider
```

The Company Knowledge module must not branch directly on provider names.

## 8. Service orchestration

`service.py` coordinates the Phase 1 flow:

```python
urls = crawler.discover(seed_url)

for url in urls:
    page = discovery.extract(url)
    normalized = normalizer.normalize(page)
    section_fingerprints = [
        fingerprinter.fingerprint_section(section)
        for section in normalized.sections
    ]
    page_fingerprint = fingerprinter.fingerprint_page(normalized)
    repository.save_page(
        normalized,
        page_fingerprint,
        section_fingerprints,
    )
```

The service must not contain:

- raw Playwright implementation details
- provider-specific LLM SDK logic
- backend-specific database details

## Documentation sync rule

Whenever the folder structure, architecture, responsibilities, or any decision documented here changes, update this document in the same PR so the documentation matches the code.

## Final Phase 1 decisions

1. Use `modules/` as the bounded application-module root.
2. Keep Phase 1 synchronous and explicit.
3. Use Strategy Pattern for crawl discovery.
4. Use async Playwright.
5. Share browser lifecycle infrastructure.
6. Keep DOM discovery factual; keep semantic interpretation optional and downstream.
7. Use a shared Repository Pattern under `app/repository`.
8. Keep database lifecycle contracts, concrete connections, and persistence schemas under `app/database`.
9. Keep database backends behind `DatabaseConnection`; SQLite is the Phase 1 backend, with PostgreSQL/MongoDB addable later without changing Company Knowledge.
10. Do not use JSON files as the source of truth.
11. Do not introduce Celery/events in Phase 1.
12. Do not hardcode business semantics from CSS classes or section positions.
13. Fingerprint normalized content with SHA-256 while ignoring DOM-only metadata.
