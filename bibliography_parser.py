"""Bibliography parser module: match citations to bibliography entries."""

import re


def match_citation(author: str, year: str, bibliography_text: str | None) -> str | None:
    """Find the bibliography entry matching the given author and year.

    Args:
        author: Author string from citation (e.g., "Smith", "Smith & Jones",
                "Smith et al.").
        year: Year string (e.g., "2020").
        bibliography_text: Full bibliography section text, or None if not found.

    Returns:
        The full matching bibliography entry string, or None if no match.
    """
    if not bibliography_text:
        return None

    entries = _parse_entries(bibliography_text)
    surname = _extract_primary_surname(author)

    for entry in entries:
        if surname.lower() in entry.lower() and year in entry:
            return entry

    return None


def _parse_entries(bibliography_text: str) -> list[str]:
    """Split bibliography text into individual entries.

    Tries double-newline splitting first. If that yields too few results
    for a long text, falls back to single-newline splitting.

    Returns:
        List of non-empty bibliography entry strings.
    """
    # Try splitting on double newlines (paragraph breaks)
    entries = re.split(r"\n\s*\n", bibliography_text)
    entries = [e.strip() for e in entries if e.strip()]

    # If we got very few entries but the text is long, try single newlines
    if len(entries) < 3 and len(bibliography_text) > 200:
        entries = bibliography_text.split("\n")
        entries = [e.strip() for e in entries if e.strip()]

    return entries


def _extract_primary_surname(author: str) -> str:
    """Extract the primary (first) surname from an author string.

    Examples:
        "Smith" -> "Smith"
        "Smith & Jones" -> "Smith"
        "Smith et al." -> "Smith"
        "Smith and Jones" -> "Smith"
    """
    # Remove "et al." suffix
    name = re.sub(r"\s+et\s+al\.?", "", author)
    # Take text before "&" or "and"
    name = re.split(r"\s+(?:&|and)\s+", name)[0]
    return name.strip()
