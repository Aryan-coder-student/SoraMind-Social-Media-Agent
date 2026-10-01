# Project Progress

Last updated: 2026-10-02

This file tracks Phase 1 implementation progress for the SoraMind Social Media Agent.

## Current status

Completed and merged pull requests on `main`: **18**

### Merged PRs

| PR | Status | Completed work | Merged |
| --- | --- | --- | --- |
| #1 | ✅ Merged | Phase 1 architecture scaffold, folder structure, repository/database boundaries, Company Knowledge module skeleton, architecture documentation | 2026-09-24 |
| #2 | ✅ Merged | Shared Playwright browser infrastructure with reusable browser/context and multi-page support | 2026-09-24 |
| #3 | ✅ Merged | Phase 1 Pydantic models for crawl results, factual page structure, and semantic knowledge | 2026-09-26 |
| #4 | ✅ Merged | Crawl URL preprocessing and validation, including relative URL resolution, anchor removal, trailing slash normalization, same-domain checks, and static asset filtering | 2026-09-26 |
| #5 | ✅ Merged | Deterministic page normalization, TextCleaner abstraction, unicode-sanity adapter, text utilities, and PageNormalizer implementation | 2026-09-27 |
| #6 | ✅ Merged | BFS website crawler, strategy-independent link extraction, controlled browser concurrency, URL deduplication, crawl limits, failure isolation, and crawl tests | 2026-09-27 |
| #7 | ✅ Merged | Crawl-level concurrency hardening and canonical URL deduplication across `www.` / non-`www.` host variants | 2026-09-27 |
| #8 | ✅ Merged | Docker runtime, Compose setup, pinned dependencies, and executable crawler CLI | 2026-09-27 |
| #9 | ✅ Merged | Factual rendered-page DOM discovery using BrowserBase with PageDocument/PageSection extraction and tests | 2026-09-27 |
| #11 | ✅ Merged | Page Discovery readiness hardening: wait for rendered React content, safe optional metadata lookup, hydration coverage, and live crawl validation | 2026-09-27 |
| #12 | ✅ Merged | Page Discovery fallback that preserves populated `<main>` content when a page has no `<section>` tags | 2026-09-27 |
| #13 | ✅ Merged | Shared LLM provider abstraction and registry with OpenAI, Anthropic/Claude, and Groq adapters | 2026-09-29 |
| #14 | ✅ Merged | Deterministic SHA-256 page and section fingerprints over normalized content, excluding DOM-only metadata and page-location fields | 2026-09-29 |
| #15 | ✅ Merged | Backend-neutral database foundation with SQLite connection adapter, SQLAlchemy page/section schema, indexes, constraints, and database tests | 2026-09-29 |
| #16 | ✅ Merged | Company Knowledge repository contract and SQLAlchemy current-state persistence with validated URL boundaries, domain↔row mapping utilities, upsert/read/delete behavior, and repository tests | 2026-09-29 |
| #17 | ✅ Merged | Explicit SQLite connection pooling for file-backed databases with configurable QueuePool settings, StaticPool for in-memory SQLite, reuse tests, and docs | 2026-09-29 |
| #18 | ✅ Merged | Immutable Company Knowledge version history with lean `pages` / `page_versions` / `section_versions` schema, current-version pointers, page-level fingerprint change detection, soft deactivation/reactivation, historical reads, schema splitting, integrity hardening, and versioning tests | 2026-09-30 |
| #19 | ✅ Merged | Deterministic section-level added / removed / changed classification with exact-fingerprint matching, heading-based changed-section matching, conservative replacement handling, and focused tests | 2026-10-01 |

> **Stacked PR note:** PR #20 (`Split Company Knowledge pipeline services`) was merged into the stacked base branch `feat/section-change-classification`, but its pipeline/service files are not present on `main` yet. It is therefore not counted as completed on `main` in this file.

## Completed Phase 1 components

### Architecture

- [x] Phase 1 folder structure
- [x] Company Knowledge module boundaries
- [x] Shared repository/database architecture
- [x] Shared browser infrastructure boundary
- [x] Architecture documentation

### Browser

- [x] Browser abstraction
- [x] Playwright runtime lifecycle
- [x] Shared Chromium browser
- [x] Reusable browser context
- [x] Multiple page/tab support
- [x] Navigation and cleanup methods

### Models

- [x] Crawl models
- [x] Page/DOM models
- [x] Knowledge models

### Crawl URL handling

- [x] Relative URL resolution
- [x] Anchor removal
- [x] Ending slash normalization
- [x] Same-domain validation
- [x] Static asset filtering
- [x] Shared skipped-extension settings

### Crawling

- [x] CrawlStrategy contract
- [x] BFS crawl implementation
- [x] Level-by-level breadth-first traversal
- [x] Controlled browser concurrency with `asyncio.Semaphore`
- [x] Concurrent level processing with `asyncio.gather`
- [x] URL deduplication using a `seen` set
- [x] Duplicate discovery prevention when URLs are queued
- [x] `max_pages` and `max_depth` limits
- [x] Page failure isolation
- [x] LinkExtractor abstraction
- [x] BrowserLinkExtractor implementation
- [x] Crawl/validation/link-extractor tests

### Page discovery

- [x] PageDiscovery contract
- [x] Shared BrowserBase integration
- [x] Final/current URL extraction
- [x] Title/meta/canonical extraction
- [x] Outermost section extraction
- [x] Section id/classes/headings/text/child-count extraction
- [x] Page cleanup and failure handling
- [x] Render-readiness wait for hydrated client content
- [x] Safe optional metadata lookup without timeout on missing elements
- [x] Fallback to populated `<main>` when no outermost sections exist
- [x] Page discovery tests
- [x] Live bounded SoraMinds crawl validation with 10 pages, 75 sections, and 0 page errors

### Runtime

- [x] requirements.txt dependency manifest
- [x] Playwright/Pydantic/unicode-sanity pinned dependencies
- [x] Dockerfile
- [x] Docker Compose runtime
- [x] Executable crawler CLI

### LLM providers

- [x] Provider-independent `LLMProvider` contract
- [x] Immutable `ProviderSpec`
- [x] `LLMRegistry` registration and provider creation
- [x] Explicit built-in provider registration
- [x] OpenAI provider adapter
- [x] Anthropic / Claude provider adapter
- [x] Groq provider adapter
- [x] Configurable model selection per provider
- [x] Provider tests without live network calls

### Fingerprinting

- [x] Deterministic SHA-256 section fingerprints
- [x] Deterministic SHA-256 page fingerprints
- [x] Canonical JSON serialization before hashing
- [x] Ordered heading level/text included in section fingerprints
- [x] Section text included in section fingerprints
- [x] Page title/meta description included in page fingerprints
- [x] Ordered section fingerprints included in page fingerprints
- [x] DOM-only metadata excluded from content fingerprints
- [x] Page/canonical URLs excluded from content fingerprints
- [x] Fingerprint determinism and change-sensitivity tests

### Database foundation

- [x] Backend-neutral `DatabaseConnection` contract
- [x] SQLite Phase 1 connection adapter
- [x] SQLAlchemy relational schema
- [x] Concern-specific schema modules: `base.py`, `page.py`, and `version.py`
- [x] Stable `pages` identity/lifecycle table
- [x] Immutable `page_versions` table
- [x] Immutable `section_versions` table
- [x] Page URL uniqueness
- [x] Per-page version-number uniqueness
- [x] Per-version section-index uniqueness
- [x] Current-version foreign-key pointer
- [x] Page/version ownership validation on current-version reads
- [x] Page and section fingerprint indexes
- [x] SQLite foreign-key enforcement
- [x] Shared in-memory SQLite test setup
- [x] Database connection/schema tests

### Repository persistence

- [x] Repository contract
- [x] SQLAlchemyRepository implementation
- [x] Page identity insert/read by validated URL
- [x] Current page read through `current_version_id`
- [x] Current page fingerprint lookup
- [x] Explicit permanent page/history delete
- [x] Domain ↔ SQLAlchemy row mapping utilities
- [x] Repository URL boundary uses Pydantic `HttpUrl`
- [x] Runtime URL validation before SQL TEXT conversion
- [x] Repository tests

### Version history and page lifecycle

- [x] Version 1 creation on first page save
- [x] New immutable page version only when the page fingerprint changes
- [x] No duplicate version when the page fingerprint is unchanged
- [x] `pages.current_version_id` points to the current immutable version
- [x] Historical page-version reads
- [x] Exact version lookup by version number
- [x] Current/latest version lookup
- [x] Complete section snapshots stored per page version
- [x] Section fingerprints retained for later section-level change detection
- [x] Soft page deactivation with `is_active`
- [x] Page reactivation without duplicate history when content is unchanged
- [x] History preserved when a page disappears
- [x] Atomic changed-version insert + current-version pointer update
- [x] Current-version ownership validation
- [x] Lean persisted schema: canonical URL and DOM-only metadata are not stored
- [x] Version-history and lifecycle tests

### Connection pooling

- [x] QueuePool for file-backed SQLite
- [x] StaticPool retained for in-memory SQLite
- [x] Configurable pool size
- [x] Configurable max overflow
- [x] Configurable pool checkout timeout
- [x] Checked-in connection reuse tests
- [x] Pooling behavior documented

### Section-level change detection

- [x] Deterministic section change classifier
- [x] Exact fingerprint matches consumed as unchanged
- [x] Same non-empty heading signature classified as changed
- [x] Unmatched previous sections classified as removed
- [x] Unmatched current sections classified as added
- [x] Reordered unchanged sections ignored
- [x] Position alone is not treated as section identity
- [x] Headingless changed sections handled conservatively as removed + added
- [x] Focused section-change tests

### Normalization

- [x] Normalizer contract
- [x] TextCleaner abstraction
- [x] unicode-sanity adapter
- [x] Whitespace cleanup
- [x] Heading cleanup
- [x] Section cleanup
- [x] Empty-section removal
- [x] Page normalization

## Current architecture direction

The normalized factual page data is the source of truth for Phase 1.

Persistence now uses immutable versions without duplicating current content:

```text
pages
= stable URL identity + lifecycle + current_version_id

page_versions
= immutable page content states

section_versions
= immutable section snapshots
```

Only knowledge-relevant persisted fields are stored. Canonical URL and DOM-only metadata remain extraction-time observations, while section fingerprints are retained for planned section-level change detection.

LLM output is treated as optional derived intelligence rather than the primary stored representation.

Planned change-intelligence flow:

```text
previous stored version
        +
new normalized version
        ↓
deterministic fingerprint / diff
        ↓
changed sections only
        ↓
optional LLM interpretation
        ↓
human-readable change summary / semantic enrichment
```

This keeps crawling and persistence deterministic while using the LLM only where semantic interpretation adds value.

## Remaining Phase 1 work

- [ ] Land PR #20 pipeline/service orchestration onto `main`
- [ ] End-to-end Phase 1 crawl → normalize → fingerprint → persist → section-diff tests
- [ ] End-to-end validation of authoritative completed-crawl reconciliation
- [ ] Full pipeline validation with the real SQLite repository and browser-backed discovery
- [ ] Optional LLM-based interpretation of changed content

Page-level and section-level deterministic change detection are complete on `main`. Pipeline/service orchestration exists in PR #20, but PR #20 was merged into its stacked feature base rather than `main`, so it still needs to be landed on `main` before being treated as complete there.

## Phase 1 flow

Primary factual pipeline:

```text
Seed URL
   ↓
URL Discovery
   ↓
Page / Section Extraction
   ↓
Normalization
   ↓
Fingerprint / Version Comparison
   ↓
Repository
   ↓
Configured database backend
(SQLite in Phase 1)
```

Optional intelligence pipeline:

```text
Changed page / section
        ↓
Deterministic diff
        ↓
LLM provider
        ↓
Change interpretation / semantic enrichment
```

Current implementation progress in that flow:

```text
Seed URL
   ↓
URL preprocessing / validation   ✅
   ↓
BFS crawl                        ✅
   ↓
Browser infrastructure          ✅
   ↓
Page discovery                  ✅
   ↓
Normalization                   ✅
   ↓
LLM provider registry            ✅
   ↓
Fingerprinting                    ✅
   ↓
Database foundation              ✅
   ↓
Repository implementation         ✅
   ↓
SQLite connection pooling         ✅
   ↓
Version history                   ✅
   ↓
Page-level change detection       ✅
   ↓
Section-level change detection    ✅
   ↓
Pipeline orchestration            ⏳
   ↓
Optional LLM interpretation      ⏳
```

## Development workflow

New implementation work follows TDD:

```text
RED      → write the failing test first
GREEN    → implement only what is needed to pass
REFACTOR → improve the design while keeping tests green
```

Tests should be added before implementation changes for new behavior and regressions.

## Tracking rule

Update this file whenever a Phase 1 implementation PR is merged so the repository always shows:

- what is complete
- which PR delivered it
- what remains next
