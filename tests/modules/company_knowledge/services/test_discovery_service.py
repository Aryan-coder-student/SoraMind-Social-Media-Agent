"""Tests for page discovery and persistence service."""

from unittest.mock import AsyncMock, Mock

import pytest

from app.modules.company_knowledge.discovery.base import PageDiscoveryBase
from app.modules.company_knowledge.fingerprint.sha256 import (
    fingerprint_page,
    fingerprint_section,
)
from app.modules.company_knowledge.models.page import (
    Heading,
    PageDocument,
    PageSection,
)
from app.modules.company_knowledge.models.version import (
    SavePageResult,
    SavePageStatus,
)
from app.modules.company_knowledge.normalization.base import NormalizerBase
from app.modules.company_knowledge.services.discovery_service import (
    CompanyKnowledgeDiscoveryService,
)
from app.repository.base import Repository


def make_page() -> PageDocument:
    return PageDocument(
        url="https://example.com/pricing",
        title="Pricing",
        sections=[
            PageSection(
                index=0,
                headings=[Heading(level=2, text="Pricing")],
                text="Current pricing",
            )
        ],
    )


@pytest.mark.asyncio
async def test_process_extracts_normalizes_fingerprints_and_persists_page() -> None:
    page = make_page()
    normalized_page = page.model_copy(update={"title": "Pricing plans"})

    discovery = Mock(spec=PageDiscoveryBase)
    discovery.extract = AsyncMock(return_value=page)

    normalizer = Mock(spec=NormalizerBase)
    normalizer.normalize.return_value = normalized_page

    repository = Mock(spec=Repository)
    save_result = SavePageResult(
        status=SavePageStatus.NEW,
        version_number=1,
    )
    repository.save_page.return_value = save_result

    service = CompanyKnowledgeDiscoveryService(
        discovery=discovery,
        normalizer=normalizer,
        repository=repository,
    )

    result = await service.process(page.url)

    expected_section_fingerprints = tuple(
        fingerprint_section(section)
        for section in normalized_page.sections
    )

    discovery.extract.assert_awaited_once_with(str(page.url))
    normalizer.normalize.assert_called_once_with(page)
    repository.save_page.assert_called_once_with(
        normalized_page,
        fingerprint_page(normalized_page),
        list(expected_section_fingerprints),
    )

    assert result.page == normalized_page
    assert result.save_result == save_result
    assert result.section_fingerprints == expected_section_fingerprints
