"""URL validation utilities for website crawling."""

from urllib.parse import urlsplit


SKIPPED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
    ".svg",
    ".ico",
    ".css",
    ".js",
    ".mp4",
    ".mp3",
    ".webm",
    ".woff",
    ".woff2",
    ".ttf",
}


def normalize_host(host: str) -> str:
    """Treat www.example.com and example.com as the same domain."""
    host = host.lower()

    if host.startswith("www."):
        return host[4:]

    return host


def is_same_domain(url: str, seed_url: str) -> bool:
    """Check whether the URL belongs to the company website."""
    url_host = urlsplit(url).hostname
    seed_host = urlsplit(seed_url).hostname

    if not url_host or not seed_host:
        return False

    return normalize_host(url_host) == normalize_host(seed_host)


def is_static_asset(url: str) -> bool:
    """Check whether the URL points to a static asset."""
    path = urlsplit(url).path.lower()

    return any(
        path.endswith(extension)
        for extension in SKIPPED_EXTENSIONS
    )


def is_crawlable_url(url: str, seed_url: str) -> bool:
    """Check whether a URL should be added to the crawl queue."""
    if not is_same_domain(url, seed_url):
        return False

    if is_static_asset(url):
        return False

    return True
