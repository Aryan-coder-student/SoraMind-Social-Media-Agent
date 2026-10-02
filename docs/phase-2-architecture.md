# Phase 2 — Autonomous Social Content Architecture

## Goal

Build the autonomous social-content layer on top of Phase 1 Company Knowledge.

Phase 1 answers:

> What does the company currently know, and what changed?

Phase 2 answers:

> What should the company post next, how should it be expressed for each platform, and when should it be published?

The normal Phase 2 flow does not require a human to choose every post topic.
The system runs a planning cycle automatically and decides what content is worth
creating while respecting a configurable publishing target.

A typical target can be 22–30 posts per configured period. The exact target and
period are configuration, not hardcoded planner behavior.

The high-level flow is:

```text
Phase 1 Company Knowledge
        +
Recent page changes
        +
Active campaigns
        +
Recent social-post history
        +
Publishing target
        ↓
Planning cycle
        ↓
Content Planner
        ↓
ContentPlan
        ↓
Knowledge Context Builder
        ↓
Platform Content Generator
        ↓
Media requirement
        ↓
Media generation when required
        ↓
Content draft
        ↓
Scheduler
        ↓
Platform publisher
```

The planner decides **what should be posted**.

The generator decides **how that idea should be written for the selected
platform**.

The media layer decides **what supporting media is required and how to produce
it**.

The scheduler decides **when the finished draft should be published**.

The publisher only performs the final platform-specific delivery.

## Core Phase 2 decision

A website change is **not** a direct publish trigger.

Recent changes are one content signal available to the planner.

The planner can choose from three content sources:

```text
Recent Company Knowledge changes
        │
Existing Company Knowledge
        │
Active campaigns / recurring product goals
        │
        └───────────────┐
                        ▼
                Content Planner
                        ↓
                   ContentPlan
```

This keeps one planning pipeline instead of building separate generation
pipelines for website changes, evergreen content, and campaigns.

## Agreed technology choices

Phase 2 reuses the technology already established in Phase 1:

- Python 3.12+
- Pydantic v2 for planner/generator models and structured LLM output
- Shared `LLMProvider` / `LLMRegistry` from `app/core/llm`
- SQLAlchemy 2.x for persistence
- SQLite for the current development backend
- `asyncio` for bounded asynchronous generation where needed
- pytest / pytest-asyncio
- Ruff
- uv

Initial scheduling should stay simple. The Phase 2 application exposes an
explicit planning-cycle entry point that can be called by cron, a hosted
scheduler, or another job runner.

Do not introduce Celery only to start Phase 2. A distributed worker system can
be added later if generation/publishing volume requires it.

Not required for the first Phase 2 implementation:

- Celery
- Redis
- Kafka / RabbitMQ
- Event bus
- Vector database
- Elasticsearch
- AI avatar provider
- Generative video provider
- Complex workflow engine

Media provider choices are deferred until the media-generation milestone.
Planning and content generation must not depend on a specific media vendor.

## Planned folder structure

Keep the Phase 2 module small and readable first. Split files only when their
responsibilities genuinely grow.

```text
app/
├── core/
│   └── llm/                         ← reused from Phase 1
│
├── database/
│   └── schemas/
│       ├── content.py               ← planned social-content persistence
│       └── campaign.py              ← only when campaign persistence is needed
│
└── modules/
    ├── company_knowledge/            ← Phase 1 source of factual knowledge
    │
    └── social_content/
        ├── pipeline.py               ← Phase 2 workflow coordinator
        ├── planner.py                ← autonomous content-topic decision
        ├── context_builder.py        ← factual Company Knowledge context
        ├── generator.py              ← platform-specific text generation
        ├── media.py                  ← media requirement / media plan
        ├── scheduler.py              ← publication-time selection
        ├── repository.py             ← social-content persistence contract
        ├── models/
        │   ├── plan.py
        │   ├── content.py
        │   └── campaign.py
        └── publishing/
            ├── base.py
            ├── linkedin.py           ← later
            ├── x.py                  ← later
            └── instagram.py          ← later
```

Do not create provider-specific publisher files until the corresponding platform
integration is actually implemented.

## 1. Planning cycle

The planning cycle is the normal starting point for autonomous content
generation.

A scheduler invokes one explicit operation:

```python
await social_content_pipeline.run_planning_cycle()
```

The planning cycle should not blindly create the entire month's content at once.
It should plan only a near-term batch so later Company Knowledge changes can
still affect upcoming posts.

Example:

```text
Monthly target: 25 posts
Already published/scheduled: 18
Remaining this month: 7
Planning horizon: next several days
        ↓
Planner creates only the next useful batch
```

The exact planning horizon belongs in configuration and can be tuned later.

### Deterministic responsibilities

Application code, not the LLM, calculates:

- how many posts are already committed
- how many posts remain for the configured period
- whether the target is already satisfied
- whether a recurring campaign is due
- which previous posts belong to the repetition-check window

The LLM is used only where semantic judgment adds value:

- which candidate topic is worth posting
- which angle is more useful
- which platform/format fits the idea
- whether a recent change is meaningful enough for social content

If the target is already satisfied, the planning cycle returns without calling
the planner LLM.

## 2. Publishing target

The publishing target is configuration.

The first version needs only:

```text
period
target_count
```

Example:

```text
period = monthly
target_count = 25
```

A later version can add minimum/maximum ranges or per-platform quotas if there
is a real requirement.

Do not put quota calculations inside prompts.

## 3. Planner inputs

The planner should receive a compact `ContentPlannerInput`, not raw database
rows or the entire website.

Conceptually:

```python
ContentPlannerInput(
    publishing_target=...,
    remaining_posts=...,
    recent_changes=...,
    knowledge_candidates=...,
    active_campaigns=...,
    recent_post_history=...,
)
```

The planner input contains five useful signals.

### Company Knowledge candidates

Current factual content from Phase 1 that can support evergreen posts:

- product capabilities
- feature explanations
- use cases
- product pages
- other current company/product knowledge

The first implementation does not require a vector database.

Use the existing persisted Company Knowledge and simple deterministic
selection/filtering. Add semantic/vector retrieval only if the existing site size
makes simple selection insufficient.

### Recent changes

Recent page-version differences from Phase 1.

Examples:

- newly added feature
- changed product capability
- pricing update
- new product/page
- removed capability

A change becomes a candidate topic only. It does not automatically create a
social post.

The first implementation should derive recent changes from the persisted
Company Knowledge version history instead of adding a second duplicate source
of truth.

If the planner needs a concise explanation of a change, the existing optional
section-change summarizer can be called when building planner context.

### Active campaigns

A campaign represents a recurring content requirement.

Examples:

```text
Promote F1 Product once per week
Feature spotlight twice per month
```

A campaign makes a topic eligible/due. The planner still chooses a fresh angle
using current Company Knowledge and recent post history.

### Recent post history

The planner must know what has already been created recently.

At minimum retain/query:

```text
topic
source_type
platform
format
created_at
scheduled_at
published_at
```

This prevents repetitive automation such as:

```text
"What is Demo Agent?"
"Introducing Demo Agent"
"Learn about Demo Agent"
"Why Demo Agent matters"
```

No embedding-based repetition system is required initially.

Use recent topics, source references, platform, and format as planner context.
Add semantic similarity only if simple history proves insufficient.

## 4. Content candidates

Before asking the planner to choose a post, application code builds candidate
content ideas from the three source types.

```text
RECENT_CHANGE
EXISTING_KNOWLEDGE
CAMPAIGN
```

Each candidate should retain factual references so the planner cannot invent a
topic that has no grounding.

Conceptually:

```python
ContentCandidate(
    source_type=...,
    topic_hint=...,
    knowledge_references=...,
    change_summary=None,
    campaign_id=None,
)
```

A knowledge reference identifies persisted Company Knowledge such as:

```text
page URL
page version
section index
```

The planner selects from supplied candidates. It should not fabricate page or
section identifiers.

## 5. Content Planner

The Content Planner owns one responsibility:

> Choose the next useful social-content idea from grounded candidates.

The planner may decide:

- topic
- source type
- reason for choosing it
- content goal
- platform
- format
- supporting knowledge references

It does not:

- write the final post
- generate an image/video
- choose an image/video vendor
- schedule a timestamp
- call social-platform APIs
- write Company Knowledge

The planner uses the shared provider-independent LLM contract.

```text
PlanningService
      ↓
ContentPlanner
      ↓
LLMProvider
```

The Company Knowledge module does not import Phase 2 planner code.

## 6. ContentPlan

`ContentPlan` is the contract between autonomous planning and downstream
generation.

Keep it small.

Conceptually:

```python
ContentPlan(
    topic=...,
    source_type=...,
    reason=...,
    goal=...,
    platform=...,
    format=...,
    knowledge_references=...,
)
```

### Source type

Initial values:

```text
RECENT_CHANGE
EXISTING_KNOWLEDGE
CAMPAIGN
```

### Platform

Initial platforms:

```text
LINKEDIN
X
INSTAGRAM
```

### Format

Formats are platform-facing content choices, for example:

```text
LinkedIn
- text_post

X
- text_post
- thread

Instagram
- poster
- carousel
- reel
```

Do not create every possible social-media format in the first model. Add formats
only when the generator supports them.

## 7. Knowledge Context Builder

After the planner chooses a `ContentPlan`, the system builds the factual input
used for content generation.

```text
ContentPlan
      ↓
knowledge_references
      ↓
Company Knowledge repository
      ↓
KnowledgeContext
```

The generator should not receive the entire website.

The context builder loads only the current facts required by the plan.

For a recent-change plan, context can contain:

```text
current section
previous section when useful
change type
optional change summary
current page title/metadata
```

For evergreen/campaign content, context can contain:

```text
selected current page/sections
relevant headings
normalized text
```

The generator treats this context as the factual source of truth.

## 8. Platform content generation

The generator receives:

```text
ContentPlan
        +
KnowledgeContext
        ↓
Platform Content Generator
```

The generator's responsibility is:

> Express the approved plan for the selected platform without inventing facts.

Initial outputs:

```text
LinkedIn
→ final post text

X
→ post or thread

Instagram
→ caption + content structure needed by the selected format
```

Keep platform-specific prompting in the generation layer, not the planner.

The generator returns a validated `ContentDraft`.

Conceptually:

```python
ContentDraft(
    plan_id=...,
    platform=...,
    format=...,
    text=...,
    media_requirement=...,
)
```

## 9. Media requirement

Media is decided after the topic/platform/format are known.

Initial media types:

```text
NONE
IMAGE
CAROUSEL
VIDEO
```

Examples:

```text
X text_post
→ NONE

Instagram poster
→ IMAGE

Instagram carousel
→ CAROUSEL

Instagram reel
→ VIDEO
```

This mapping should be deterministic where the selected format already implies
the media type.

Do not call an LLM to decide something that is already implied by
`platform + format`.

## 10. Media planning and generation

Media generation is a downstream capability.

A media plan can describe:

- poster copy/layout requirements
- carousel slide structure
- video/reel scenes
- voiceover script when needed
- factual visual references

The first implementation should prefer simple, controllable output:

```text
Poster
→ static generated/template image

Carousel
→ generated slide images

Video/Reel
→ slides/screenshots
→ optional TTS
→ captions
→ deterministic renderer such as FFmpeg
```

AI avatars and generative-video providers are optional later implementations.

The application should depend on a small media-generation boundary rather than
vendor-specific APIs.

## 11. Content lifecycle and persistence

Phase 2 needs persistence because the planner must know what has already been
planned, generated, scheduled, and published.

Use one social-content aggregate initially instead of creating many relational
tables prematurely.

Conceptual lifecycle:

```text
PLANNED
   ↓
GENERATED
   ↓
SCHEDULED
   ↓
PUBLISHED

or

FAILED
```

A first `content_items` persistence model can retain:

```text
id
topic
source_type
reason
goal
platform
format
knowledge_references
status
text_content
media_type
media_payload
created_at
scheduled_at
published_at
external_post_id
last_error
```

Only split plans, drafts, schedules, and publishing records into separate tables
if lifecycle or query requirements make the single aggregate difficult to
maintain.

### Repository boundary

Do not add unrelated social-content methods to the Phase 1 Company Knowledge
repository.

Create a Phase 2 repository contract for the social-content aggregate:

```text
SocialContentRepository
├── save_plan(...)
├── save_draft(...)
├── mark_scheduled(...)
├── mark_published(...)
├── mark_failed(...)
├── get_recent_content(...)
└── count_committed_content(...)
```

The exact method set should be added only as implementation requires it.

This keeps Company Knowledge persistence and social-content lifecycle separate.

## 12. Scheduling

Scheduling happens after a draft is successfully generated.

```text
ContentDraft
      ↓
SchedulingService
      ↓
scheduled_at
```

Scheduling should consider:

- remaining posts in the period
- already scheduled posts
- platform
- campaign constraints
- reasonable spacing

The first version should use deterministic scheduling rules.

Do not ask the LLM to calculate timestamps.

A later system can optimize posting time from engagement analytics if those data
become available.

## 13. Publishing

Publishing is the final external side effect.

Use one small provider-independent contract:

```python
class Publisher(ABC):
    async def publish(self, content: ScheduledContent) -> PublishResult:
        ...
```

Later adapters can implement:

```text
LinkedInPublisher
XPublisher
InstagramPublisher
```

Publishing adapters own:

- authentication
- platform request payloads
- media upload details
- API errors
- returned external post identifiers

The planner and generator must not contain social-platform SDK/API calls.

Publishing must be idempotent enough to avoid duplicate posts when a retry
occurs.

## 14. Pipeline orchestration

`SocialContentPipeline` coordinates Phase 2 without owning implementation
details.

Conceptually:

```text
run_planning_cycle()
        ↓
calculate remaining target
        ↓
build grounded candidates
        ↓
ContentPlanner
        ↓
persist ContentPlan
        ↓
KnowledgeContextBuilder
        ↓
PlatformContentGenerator
        ↓
persist ContentDraft
        ↓
resolve/generate media
        ↓
SchedulingService
        ↓
persist scheduled time
        ↓
Publisher runs when due
```

The pipeline must not contain:

- Company Knowledge crawl logic
- raw SQLAlchemy queries
- provider-specific LLM SDK logic
- media-vendor-specific API logic
- social-platform-specific API logic
- prompt parsing details
- semantic candidate-ranking heuristics hardcoded in orchestration

## 15. Failure boundaries

Failures should not corrupt completed work.

Examples:

```text
Planner failure
→ no ContentPlan persisted as ready

Text generation failure
→ plan remains available for retry

Media generation failure
→ draft remains generated; media step can retry

Scheduling failure
→ generated draft remains available

Publishing failure
→ scheduled content remains retryable
→ do not create a duplicate plan
```

Persist lifecycle status and enough error context for retries.

Do not make one platform failure roll back unrelated content already generated
for other platforms.

## 16. Testing strategy

Follow the existing TDD workflow:

```text
RED → GREEN → REFACTOR
```

### Planner tests

Cover:

- no planner call when publishing target is already met
- correct remaining-post calculation
- candidate creation from recent changes
- candidate creation from existing knowledge
- due campaign candidate creation
- recent history supplied for repetition control
- planner output must reference supplied candidates
- invalid platform/format output rejected
- malformed LLM output rejected
- provider failures preserve useful context

### Context-builder tests

Cover:

- only requested Company Knowledge is loaded
- inactive/stale page data is not preferred over current knowledge
- persisted page/version/section references are respected
- missing references fail clearly

### Generator tests

Cover:

- platform-specific output validation
- factual context is passed to the LLM
- unsupported formats rejected
- no live LLM network dependency in tests

### Scheduling tests

Cover:

- no duplicate schedule for one content item
- deterministic spacing
- target/period boundaries
- campaign timing constraints

### Publisher tests

Use fake platform adapters.

Cover:

- successful publish status
- failed publish remains retryable
- external post ID stored
- retry does not duplicate a successful post

## 17. Phase 2 implementation order

Implement Phase 2 in small pull requests.

### PR 1 — Architecture and planner models

- Phase 2 architecture
- publishing-target model/configuration
- `ContentCandidate`
- `ContentPlannerInput`
- `ContentPlan`
- platform/source/format enums
- tests for model validation

### PR 2 — Autonomous Content Planner

- remaining-post calculation
- candidate collection
- recent-history input
- provider-independent planner
- structured LLM plan output
- planner tests

### PR 3 — Knowledge Context Builder

- Company Knowledge reads for selected references
- recent-change context
- evergreen/campaign context
- focused tests

### PR 4 — Platform Content Generator

- LinkedIn text post
- X post/thread
- Instagram caption/content structure
- validated `ContentDraft`
- generator tests

### PR 5 — Social content persistence

- social-content repository
- `content_items` lifecycle storage
- recent-content history queries
- committed-post counting
- persistence tests

This can move earlier if planner implementation needs persistent history before
PR 4. Keep the dependency order practical rather than forcing the PR numbering.

### PR 6 — Media planning

- deterministic media requirement
- poster/carousel/reel media-plan models
- tests

### PR 7 — Media generation

- simple image/carousel generation
- simple slide/reel rendering
- TTS only when required
- provider boundary for future media tools

### PR 8 — Scheduling

- deterministic schedule allocation
- scheduled lifecycle status
- scheduler entry point
- tests

### PR 9 — Publishing adapters

- platform-independent publisher contract
- LinkedIn/X/Instagram adapters as credentials/API access allow
- retry/idempotency tests

## Documentation sync rule

Whenever Phase 2 folder structure, models, pipeline responsibilities, persistence
shape, or a final architecture decision changes, update this document in the
same PR.

## Final Phase 2 decisions

1. The planning cycle is the normal autonomous starting point.
2. Website changes are planner signals, not automatic publish commands.
3. Use one content-planning pipeline for recent changes, existing knowledge, and campaigns.
4. Company Knowledge remains the factual source of truth.
5. Application code calculates quotas, due campaigns, time windows, and schedules.
6. Use the LLM only for semantic decisions and content generation.
7. The planner chooses what to post; it does not write final copy or publish.
8. `ContentPlan` is the boundary between planning and generation.
9. Every plan keeps factual Company Knowledge references.
10. The generator receives only relevant factual context, not the entire crawled website.
11. Do not introduce a vector database until simple knowledge selection is insufficient.
12. Keep media decisions downstream from topic/platform/format selection.
13. Do not choose or hardcode an avatar/video vendor in the core architecture.
14. Start media generation with simple controllable output before advanced generative video.
15. Persist content lifecycle so history, retries, scheduling, and repetition control are reliable.
16. Keep Phase 2 social-content persistence separate from Phase 1 Company Knowledge persistence.
17. Schedule only successfully generated drafts.
18. Publishing adapters own platform API details and must be retry-safe.
19. Plan a near-term batch rather than generating the entire month at once.
20. Prefer KISS: introduce abstractions only for real responsibility or provider boundaries.
