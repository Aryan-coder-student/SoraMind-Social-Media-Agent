"""Tests for the manual SoraMinds crawl JSON runner."""

import json

import pytest

from app.modules.company_knowledge.models.crawl import CrawlResult, DiscoveredURL
from app.modules.company_knowledge.models.page import PageDocument


class FakeCrawler:
    """Return a predefined crawl result."""

    async def discover(self, seed_url: str) -> CrawlResult:
        return CrawlResult(
            seed_url=seed_url,
            urls=[
                DiscoveredURL(
                    url=seed_url,
                    depth=0,
                ),
                DiscoveredURL(
                    url="https://www.soraminds.com/about",
                    depth=1,
                    discovered_from=seed_url,
                ),
            ],
            visited_count=2,
            skipped_count=1,
        )


class FakeDiscovery:
    """Return one page and fail another so the runner can continue."""

    async def extract(self, url: str) -> PageDocument:
        if url.endswith("/about"):
            raise RuntimeError("page failed")

        return PageDocument(
            url=url,
            title="  SoraMinds  ",
            sections=[],
        )


class FakeNormalizer:
    """Return a visibly normalized copy for assertions."""

    def normalize(self, page: PageDocument) -> PageDocument:
        return page.model_copy(
            update={
                "title": "SoraMinds",
            }
        )


@pytest.mark.asyncio
async def test_collect_crawl_output_includes_raw_and_normalized_pages() -> None:
    from run_soraminds_crawl import collect_crawl_output

    output = await collect_crawl_output(
        crawler=FakeCrawler(),
        discovery=FakeDiscovery(),
        normalizer=FakeNormalizer(),
        seed_url="https://www.soraminds.com/",
    )

    assert output["crawl"]["visited_count"] == 2
    assert len(output["pages"]) == 1
    assert output["pages"][0]["crawl"]["depth"] == 0
    assert output["pages"][0]["page"]["title"] == "  SoraMinds  "
    assert output["pages"][0]["normalized_page"]["title"] == "SoraMinds"
    assert output["page_errors"] == [
        {
            "url": "https://www.soraminds.com/about",
            "error": "RuntimeError: page failed",
        }
    ]


def test_save_json_creates_parent_directory(tmp_path) -> None:
    from run_soraminds_crawl import save_json

    output_path = tmp_path / "crawl" / "soraminds.json"
    payload = {
        "name": "SoraMinds",
        "pages": [],
    }

    save_json(payload, output_path)

    saved = json.loads(output_path.read_text(encoding="utf-8"))

    assert saved == payload


def test_defaults_target_soraminds() -> None:
    from run_soraminds_crawl import (
        DEFAULT_OUTPUT_PATH,
        DEFAULT_SEED_URL,
    )

    assert DEFAULT_SEED_URL == "https://www.soraminds.com/"
    assert DEFAULT_OUTPUT_PATH.name == "soraminds_crawl_output.json"
