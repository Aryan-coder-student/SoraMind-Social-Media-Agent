"""Run the Phase 1 SoraMinds crawl pipeline and save JSON output."""

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

from app.infrastructure.browser.browser import Browser
from app.modules.company_knowledge.crawl.bfs import BFSCrawlStrategy
from app.modules.company_knowledge.crawl.link_extractor import BrowserLinkExtractor
from app.modules.company_knowledge.discovery.page_discovery import PageDiscovery
from app.modules.company_knowledge.normalization.normalize import PageNormalizer
from app.modules.company_knowledge.normalization.text_cleaner import (
    UnicodeSanityAdapter,
)

DEFAULT_SEED_URL = "https://www.soraminds.com/"
DEFAULT_OUTPUT_PATH = Path("soraminds_crawl_output.json")


async def collect_crawl_output(
    crawler: Any,
    discovery: Any,
    normalizer: Any,
    seed_url: str,
) -> dict[str, Any]:
    """Collect crawl metadata plus raw and normalized page documents."""
    crawl_result = await crawler.discover(seed_url)

    pages: list[dict[str, Any]] = []
    page_errors: list[dict[str, str]] = []

    for discovered_url in crawl_result.urls:
        page_url = str(discovered_url.url)

        try:
            page = await discovery.extract(page_url)
            normalized_page = normalizer.normalize(page)
        except Exception as error:
            page_errors.append(
                {
                    "url": page_url,
                    "error": f"{type(error).__name__}: {error}",
                }
            )
            continue

        pages.append(
            {
                "crawl": discovered_url.model_dump(mode="json"),
                "page": page.model_dump(mode="json"),
                "normalized_page": normalized_page.model_dump(mode="json"),
            }
        )

    return {
        "crawl": crawl_result.model_dump(mode="json"),
        "pages": pages,
        "page_errors": page_errors,
    }


def save_json(payload: dict[str, Any], output_path: Path) -> None:
    """Write crawl output as readable UTF-8 JSON."""
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    output_path.write_text(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


async def run(
    seed_url: str,
    output_path: Path,
    max_pages: int,
    max_depth: int,
    concurrency: int,
    headed: bool,
) -> dict[str, Any]:
    """Run the current pre-LLM Company Knowledge pipeline."""
    browser = Browser(
        headless=not headed,
    )

    try:
        await browser.start()

        link_extractor = BrowserLinkExtractor(
            browser,
            concurrency=concurrency,
        )
        crawler = BFSCrawlStrategy(
            link_extractor,
            max_pages=max_pages,
            max_depth=max_depth,
            concurrency=concurrency,
        )
        discovery = PageDiscovery(browser)
        normalizer = PageNormalizer(
            UnicodeSanityAdapter(),
        )

        payload = await collect_crawl_output(
            crawler=crawler,
            discovery=discovery,
            normalizer=normalizer,
            seed_url=seed_url,
        )
    finally:
        await browser.close()

    save_json(
        payload,
        output_path,
    )

    return payload


def parse_args() -> argparse.Namespace:
    """Parse manual crawl-runner options."""
    parser = argparse.ArgumentParser(
        description=(
            "Crawl SoraMinds, extract factual page structure, "
            "normalize it, and save the result as JSON."
        )
    )
    parser.add_argument(
        "--url",
        default=DEFAULT_SEED_URL,
        help="Seed URL to crawl.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Path for the JSON output.",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=100,
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=5,
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=5,
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Show Chromium while crawling.",
    )

    return parser.parse_args()


def main() -> None:
    """Run the crawl and report where the JSON snapshot was written."""
    args = parse_args()

    payload = asyncio.run(
        run(
            seed_url=args.url,
            output_path=args.output,
            max_pages=args.max_pages,
            max_depth=args.max_depth,
            concurrency=args.concurrency,
            headed=args.headed,
        )
    )

    print(
        f"Saved {len(payload['pages'])} pages "
        f"to {args.output}"
    )

    if payload["page_errors"]:
        print(
            f"Page extraction errors: "
            f"{len(payload['page_errors'])}"
        )


if __name__ == "__main__":
    main()
