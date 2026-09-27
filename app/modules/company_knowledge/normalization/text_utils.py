"""Pure utility functions for webpage normalization."""


from app.modules.company_knowledge.models.page import PageSection


def clean_unwanted_space(text: str) -> str:
    """Collapse repeated spaces and remove unnecessary blank lines."""
    lines = [
        " ".join(line.split())
        for line in text.splitlines()
    ]

    cleaned_text = "\n".join(
        line
        for line in lines
        if line
    )

    return cleaned_text


def remove_empty_sections(
    sections: list[PageSection],
) -> list[PageSection]:
    """Remove sections that contain no useful text or headings."""
    cleaned_sections = [
        section
        for section in sections
        if section.text or section.headings
    ]

    return cleaned_sections
