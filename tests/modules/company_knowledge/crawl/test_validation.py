"""Tests for crawl URL validation."""

from app.modules.company_knowledge.crawl.validation import (
    is_crawlable_url,
    is_same_domain,
    is_static_asset,
    normalize_host,
)


def test_normalize_host_ignores_case_and_www() -> None:
    assert normalize_host("WWW.Example.COM") == "example.com"


def test_same_domain_treats_www_as_same_site() -> None:
    assert is_same_domain(
        "https://www.example.com/about",
        "https://example.com/",
    )


def test_same_domain_rejects_external_site() -> None:
    assert not is_same_domain(
        "https://external.example/about",
        "https://example.com/",
    )


def test_static_asset_detection_uses_url_path() -> None:
    assert is_static_asset(
        "https://example.com/assets/logo.PNG?version=2"
    )


def test_pdf_is_not_treated_as_static_asset() -> None:
    assert not is_static_asset(
        "https://example.com/company-profile.pdf"
    )


def test_crawlable_url_accepts_internal_page() -> None:
    assert is_crawlable_url(
        "https://www.example.com/about",
        "https://example.com/",
    )


def test_crawlable_url_rejects_static_asset() -> None:
    assert not is_crawlable_url(
        "https://example.com/assets/app.js",
        "https://example.com/",
    )


def test_crawlable_url_rejects_external_page() -> None:
    assert not is_crawlable_url(
        "https://external.example/page",
        "https://example.com/",
    )
