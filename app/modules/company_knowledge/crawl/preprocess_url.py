"""URL preprocessing utilities for website crawling."""

from urllib.parse import urljoin, urlsplit, urlunsplit


def resolve_url(base_url: str, href: str) -> str:
    """Convert a relative URL into an absolute URL."""
    return urljoin(base_url, href)


def remove_anchor(url: str) -> str:
    """Remove the #section part from a URL."""
    parsed_url = urlsplit(url)

    return urlunsplit(
        (
            parsed_url.scheme,
            parsed_url.netloc,
            parsed_url.path,
            parsed_url.query,
            "",
        )
    )


def normalize_end_slash(url: str) -> str:
    """Remove the ending slash except for the root URL."""
    parsed_url = urlsplit(url)
    path = parsed_url.path

    if path != "/":
        path = path.rstrip("/")

    return urlunsplit(
        (
            parsed_url.scheme,
            parsed_url.netloc,
            path,
            parsed_url.query,
            "",
        )
    )


def preprocess_url(base_url: str, href: str) -> str:
    """Resolve and normalize a discovered URL."""
    url = resolve_url(base_url, href)
    url = remove_anchor(url)
    url = normalize_end_slash(url)

    return url
