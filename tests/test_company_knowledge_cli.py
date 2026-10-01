"""Tests for the browser-backed Company Knowledge command."""

from unittest.mock import AsyncMock, Mock

import pytest
from pydantic import HttpUrl

from app.company_knowledge_cli import (
    CompanyKnowledgeRuntime,
    PipelineCommand,
    build_report,
    parse_options,
)
from app.database.connections.sqlite import SQLiteConnection
from app.infrastructure.browser.base import BrowserBase
from app.modules.company_knowledge.models.version import (
    SavePageResult,
    SavePageStatus,
)
from app.modules.company_knowledge.pipeline import CompanyKnowledgePipeline
from app.modules.company_knowledge.services.base import PageBuildResult


def test_parse_options_builds_bounded_pipeline_command() -> None:
    options = parse_options(
        [
            "build",
            "https://example.com",
            "--database-url",
            "sqlite:///knowledge.db",
            "--max-pages",
            "12",
            "--max-depth",
            "3",
            "--concurrency",
            "4",
            "--headed",
        ]
    )

    assert options.command == PipelineCommand.BUILD
    assert options.seed_url == "https://example.com"
    assert options.database_url == "sqlite:///knowledge.db"
    assert options.max_pages == 12
    assert options.max_depth == 3
    assert options.concurrency == 4
    assert options.headless is False


@pytest.mark.asyncio
async def test_runtime_build_owns_resource_lifecycle() -> None:
    browser = Mock(spec=BrowserBase)
    browser.start = AsyncMock()
    browser.close = AsyncMock()
    database = Mock(spec=SQLiteConnection)
    pipeline = Mock(spec=CompanyKnowledgePipeline)
    pipeline.run = AsyncMock(return_value=[])

    runtime = CompanyKnowledgeRuntime(
        browser=browser,
        database=database,
        pipeline=pipeline,
    )

    results = await runtime.build("https://example.com")

    assert results == []
    database.create_tables.assert_called_once_with()
    browser.start.assert_awaited_once_with()
    pipeline.run.assert_awaited_once_with("https://example.com")
    browser.close.assert_awaited_once_with()
    database.close.assert_called_once_with()


@pytest.mark.asyncio
async def test_runtime_closes_resources_after_pipeline_failure() -> None:
    browser = Mock(spec=BrowserBase)
    browser.start = AsyncMock()
    browser.close = AsyncMock()
    database = Mock(spec=SQLiteConnection)
    pipeline = Mock(spec=CompanyKnowledgePipeline)
    pipeline.run_and_deactivate_missing_pages = AsyncMock(
        side_effect=RuntimeError("pipeline failed")
    )

    runtime = CompanyKnowledgeRuntime(
        browser=browser,
        database=database,
        pipeline=pipeline,
    )

    with pytest.raises(RuntimeError, match="pipeline failed"):
        await runtime.build_and_deactivate_missing_pages(
            "https://example.com"
        )

    browser.close.assert_awaited_once_with()
    database.close.assert_called_once_with()


def test_build_report_serializes_persistence_results() -> None:
    results = [
        PageBuildResult(
            url=HttpUrl("https://example.com/pricing"),
            save_result=SavePageResult(
                status=SavePageStatus.CHANGED,
                version_number=2,
            ),
        )
    ]

    report = build_report(results)

    assert report == {
        "processed_pages": 1,
        "pages": [
            {
                "url": "https://example.com/pricing",
                "status": "changed",
                "version_number": 2,
                "section_changes": None,
            }
        ],
    }
