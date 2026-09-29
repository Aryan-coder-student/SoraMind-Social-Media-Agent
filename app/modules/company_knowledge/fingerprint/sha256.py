"""SHA-256 fingerprints for normalized Company Knowledge content."""

import hashlib
import json

from app.modules.company_knowledge.fingerprint.base import (
    page_payload,
    section_payload,
)
from app.modules.company_knowledge.models.page import PageDocument, PageSection


def fingerprint_section(section: PageSection) -> str:
    """Hash ordered headings and normalized section text."""
    return _fingerprint(section_payload(section))


def fingerprint_page(page: PageDocument) -> str:
    """Hash page metadata and ordered section content fingerprints."""
    section_fingerprints = [
        fingerprint_section(section)
        for section in page.sections
    ]
    return _fingerprint(page_payload(page, section_fingerprints))


def _fingerprint(payload: object) -> str:
    """Serialize a payload canonically and return its SHA-256 digest."""
    serialized_payload = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(serialized_payload.encode("utf-8")).hexdigest()
