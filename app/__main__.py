"""Command-line entry point for the website crawler."""

import argparse
import asyncio

from app.infrastructure.browser.browser import Browser
from app.modules.company_knowledge.crawl.bfs import BFSCrawlStrategy
from app.modules.company_knowledge.crawl.link_extractor import BrowserLinkExtractor


def parse_args() -> argparse.Namespace:
    """Parse crawler command-line arguments."""
    parser = argparse.ArgumentParser(description="Discover internal website URLs.")
    parser.add_argument("url", help="Seed URL to crawl.")
    parser.add_argument("--max-pages", type=int, default=100)
    parser.add_argument("--max-depth", type=int, default=5)
    parser.add_argument("--concurrency", type=int, default=5)
    return parser.parse_args()


async def crawl(args: argparse.Namespace) -> None:
    """Run the crawler and print its result as JSON."""
    browser = Browser()

    try:
        await browser.start()
        link_extractor = BrowserLinkExtractor(
            browser,
            concurrency=args.concurrency,
        )
        strategy = BFSCrawlStrategy(
            link_extractor,
            max_pages=args.max_pages,
            max_depth=args.max_depth,
            concurrency=args.concurrency,
        )
        result = await strategy.discover(args.url)
        print(result.model_dump_json(indent=2))
    finally:
        await browser.close()


def main() -> None:
    """Run the asynchronous crawler from a synchronous command line."""
    asyncio.run(crawl(parse_args()))


if __name__ == "__main__":
    main()
