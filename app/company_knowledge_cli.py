"""Run the browser-backed Company Knowledge pipeline with SQLite."""

import argparse
import asyncio
import json
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from app.database.connections.sqlite import SQLiteConnection
from app.infrastructure.browser.base import BrowserBase
from app.infrastructure.browser.browser import Browser
from app.modules.company_knowledge.crawl.bfs import BFSCrawlStrategy
from app.modules.company_knowledge.crawl.link_extractor import BrowserLinkExtractor
from app.modules.company_knowledge.discovery.page_discovery import PageDiscovery
from app.modules.company_knowledge.normalization.normalize import PageNormalizer
from app.modules.company_knowledge.normalization.text_cleaner import (
    UnicodeSanityAdapter,
)
from app.modules.company_knowledge.pipeline import CompanyKnowledgePipeline
from app.modules.company_knowledge.services.base import PageBuildResult
from app.modules.company_knowledge.services.change_service import (
    CompanyKnowledgeChangeService,
)
from app.modules.company_knowledge.services.discovery_service import (
    CompanyKnowledgeDiscoveryService,
)
from app.repository.operations.sqlalchemy import SQLAlchemyRepository
from app.settings import SQLITE_DATABASE_URL


class PipelineCommand(str, Enum):
    """Supported browser-backed pipeline operations."""

    BUILD = "build"
    BUILD_AND_DEACTIVATE = "build-and-deactivate-missing-pages"


@dataclass(frozen=True)
class PipelineOptions:
    """Configuration for one browser-backed pipeline execution."""

    command: PipelineCommand
    seed_url: str
    database_url: str
    max_pages: int
    max_depth: int
    concurrency: int
    headless: bool


class DatabaseLifecycle(Protocol):
    """Database operations owned by the command runtime."""

    def create_tables(self) -> None:
        """Create missing persistence tables."""
        ...

    def close(self) -> None:
        """Release database resources."""
        ...


PipelineOperation = Callable[[str], Awaitable[list[PageBuildResult]]]


class CompanyKnowledgeRuntime:
    """Own browser and database lifecycle around one pipeline run."""

    def __init__(
        self,
        browser: BrowserBase,
        database: DatabaseLifecycle,
        pipeline: CompanyKnowledgePipeline,
    ) -> None:
        self.browser = browser
        self.database = database
        self.pipeline = pipeline

    async def build(self, seed_url: str) -> list[PageBuildResult]:
        """Process discovered pages without deactivating absent URLs."""
        return await self._execute(seed_url, self.pipeline.run)

    async def build_and_deactivate_missing_pages(
        self,
        seed_url: str,
    ) -> list[PageBuildResult]:
        """Process a complete crawl and deactivate absent URLs."""
        return await self._execute(
            seed_url,
            self.pipeline.run_and_deactivate_missing_pages,
        )

    async def _execute(
        self,
        seed_url: str,
        operation: PipelineOperation,
    ) -> list[PageBuildResult]:
        """Run one operation and always release runtime resources."""
        try:
            self.database.create_tables()
            await self.browser.start()
            return await operation(seed_url)
        finally:
            try:
                await self.browser.close()
            finally:
                self.database.close()


def parse_options(arguments: Sequence[str] | None = None) -> PipelineOptions:
    """Parse command-line arguments into immutable runtime options."""
    parser = argparse.ArgumentParser(
        description=(
            "Crawl rendered pages, normalize and fingerprint their content, "
            "and persist immutable versions to SQLite."
        )
    )
    parser.add_argument(
        "command",
        type=PipelineCommand,
        choices=list(PipelineCommand),
    )
    parser.add_argument("seed_url", help="Seed URL to crawl.")
    parser.add_argument(
        "--database-url",
        default=SQLITE_DATABASE_URL,
        help="SQLAlchemy SQLite URL for persisted page versions.",
    )
    parser.add_argument("--max-pages", type=int, default=100)
    parser.add_argument("--max-depth", type=int, default=5)
    parser.add_argument("--concurrency", type=int, default=5)
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Show Chromium while the pipeline runs.",
    )

    parsed = parser.parse_args(arguments)
    return PipelineOptions(
        command=parsed.command,
        seed_url=parsed.seed_url,
        database_url=parsed.database_url,
        max_pages=parsed.max_pages,
        max_depth=parsed.max_depth,
        concurrency=parsed.concurrency,
        headless=not parsed.headed,
    )


def create_runtime(options: PipelineOptions) -> CompanyKnowledgeRuntime:
    """Compose concrete browser, pipeline, repository, and database adapters."""
    browser = Browser(headless=options.headless)
    database = SQLiteConnection(options.database_url)
    repository = SQLAlchemyRepository(database.create_session_factory())

    link_extractor = BrowserLinkExtractor(
        browser,
        concurrency=options.concurrency,
    )
    crawler = BFSCrawlStrategy(
        link_extractor,
        max_pages=options.max_pages,
        max_depth=options.max_depth,
        concurrency=options.concurrency,
    )
    discovery_service = CompanyKnowledgeDiscoveryService(
        discovery=PageDiscovery(browser),
        normalizer=PageNormalizer(UnicodeSanityAdapter()),
        repository=repository,
    )
    change_service = CompanyKnowledgeChangeService(repository=repository)
    pipeline = CompanyKnowledgePipeline(
        crawler=crawler,
        discovery_service=discovery_service,
        change_service=change_service,
        repository=repository,
    )

    return CompanyKnowledgeRuntime(
        browser=browser,
        database=database,
        pipeline=pipeline,
    )


def build_report(results: Sequence[PageBuildResult]) -> dict[str, object]:
    """Build a JSON-compatible report from pipeline persistence results."""
    pages = []
    for result in results:
        section_changes = result.section_changes
        pages.append(
            {
                "url": str(result.url),
                "status": result.save_result.status.value,
                "version_number": result.save_result.version_number,
                "section_changes": (
                    section_changes.model_dump(mode="json")
                    if section_changes is not None
                    else None
                ),
            }
        )

    return {
        "processed_pages": len(pages),
        "pages": pages,
    }


async def execute(options: PipelineOptions) -> dict[str, object]:
    """Execute the selected pipeline command and build its report."""
    runtime = create_runtime(options)

    if options.command == PipelineCommand.BUILD:
        results = await runtime.build(options.seed_url)
    else:
        results = await runtime.build_and_deactivate_missing_pages(
            options.seed_url
        )

    return build_report(results)


def main() -> None:
    """Run the selected pipeline command and print JSON results."""
    report = asyncio.run(execute(parse_options()))
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
