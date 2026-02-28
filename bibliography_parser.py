"""Bibliography parser module: match citations to bibliography entries."""

import re

# Matches DOI URLs in bibliography entries.
# Handles: https://doi.org/..., http://doi.org/..., doi:...
_DOI_URL_RE = re.compile(r'https?://doi\.org/\S+|doi:\s*\S+', re.IGNORECASE)

# Matches bare DOIs like: 10.1109/ASONAM49781.2020.9381415
# Works whether preceded by "doi:", "https://doi.org/", or just whitespace.
_DOI_RE = re.compile(r"\b(10\.\d{4,}(?:\.\d+)*/\S+)")


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

    entries = parse_entries(bibliography_text)
    surname = _extract_primary_surname(author)

    surname_pattern = re.compile(r'\b' + re.escape(surname) + r'\b', re.IGNORECASE)
    for entry in entries:
        if surname_pattern.search(entry) and year in entry:
            return entry

    return None


def parse_entries(bibliography_text: str) -> list[str]:
    """Split bibliography text into individual entries.

    Uses three strategies in order:
    1. Double-newline splitting (well-formatted DOCX).
    2. Single-newline splitting (partially formatted PDF).
    3. DOI-boundary splitting (PDF where newlines between entries are lost).

    In strategies 1 and 2, any entry that still contains multiple DOIs
    is further split by DOI boundaries.
    """
    # Strategy 1: double-newline (paragraphs)
    entries = re.split(r'\n\s*\n', bibliography_text)
    entries = [e.strip() for e in entries if e.strip()]
    if len(entries) >= 3:
        return _heal_merged_entries(entries)

    # Strategy 2: single newline
    entries = bibliography_text.split('\n')
    entries = [e.strip() for e in entries if e.strip()]
    if len(entries) >= 3:
        return _heal_merged_entries(entries)

    # Strategy 3: DOI-boundary splitting for flat text
    return _split_by_doi_boundaries(bibliography_text)


def _heal_merged_entries(entries: list[str]) -> list[str]:
    """Split any entries that still contain multiple DOIs (merged entries)."""
    result = []
    for entry in entries:
        if len(_DOI_URL_RE.findall(entry)) > 1:
            result.extend(_split_by_doi_boundaries(entry))
        else:
            result.append(entry)
    return result


def _split_by_doi_boundaries(text: str) -> list[str]:
    """Split a text block into entries using DOI URLs as entry terminators.

    Each bibliography entry typically ends with a DOI URL. This function
    finds all DOI matches, and treats the text between them as individual
    entries. Text after the last DOI (entries without DOIs) is kept as-is.
    """
    doi_matches = list(_DOI_URL_RE.finditer(text))

    if not doi_matches:
        # No DOIs found: fall back to author-pattern splitting
        return _split_by_author_pattern(text)

    entries = []
    prev_start = 0

    for m in doi_matches:
        entry = text[prev_start:m.end()].strip()
        if entry:
            entries.append(entry)
        # Advance past whitespace to the start of the next entry
        next_pos = m.end()
        while next_pos < len(text) and text[next_pos] in ' \t\n\r':
            next_pos += 1
        prev_start = next_pos

    # Capture any remaining text after the last DOI (entries with no DOI)
    remaining = text[prev_start:].strip()
    if remaining:
        entries.append(remaining)

    return [e for e in entries if e.strip()]


def _split_by_author_pattern(text: str) -> list[str]:
    """Split on APA author name patterns for entries that lack DOIs.

    Matches positions where text looks like the start of a new entry:
    a capital surname followed by a comma and an initial or first name.
    """
    parts = re.split(
        r'(?<=\S)\s+(?=[A-Z][a-zA-Z\u00C0-\u017E\-\']+,\s+(?:[A-Z]\.|\w+\s+[A-Z]\.))',
        text,
    )
    return [p.strip() for p in parts if p.strip()] or [text]


def parse_entry_metadata(entry_text: str) -> dict:
    """Extract structured metadata from a bibliography entry for display.

    Returns dict with keys: parsed_author, parsed_year, parsed_title.
    All values are best-effort heuristic extractions.
    """
    # Extract year (first 4-digit number that looks like a publication year)
    year_match = re.search(r'\b((?:19|20)\d{2})\b', entry_text)
    parsed_year = year_match.group(1) if year_match else None

    # Extract primary author (text before the first comma or period)
    author_match = re.match(
        r'^([A-Z\u00C0-\u024F][a-zA-Z\u00C0-\u024F\-\']+)', entry_text
    )
    parsed_author = author_match.group(1) if author_match else None

    # Extract title heuristic: text after year in parens/period, before next period
    # Common APA pattern: Author, A. (2020). Title of the paper. Journal...
    title_match = re.search(r'\(\d{4}[a-z]?\)\.\s*(.+?)\.', entry_text)
    if not title_match:
        # Alternate pattern: year followed by period then title
        title_match = re.search(r'\d{4}[a-z]?\.\s*(.+?)\.', entry_text)
    parsed_title = title_match.group(1).strip() if title_match else None

    return {
        "parsed_author": parsed_author,
        "parsed_year": parsed_year,
        "parsed_title": parsed_title,
    }


def extract_doi(entry_text: str) -> str | None:
    """Extract a DOI from a bibliography entry string.

    Handles: https://doi.org/10.xxxx/..., doi:10.xxxx/..., or bare 10.xxxx/...
    Returns the bare DOI (e.g., "10.1234/foo") or None.
    """
    match = _DOI_RE.search(entry_text)
    if not match:
        return None
    doi = match.group(1).rstrip(".,;)")
    return doi


def _extract_primary_surname(author: str) -> str:
    """Extract the primary (first) surname from an author string.

    Examples:
        "Smith" -> "Smith"
        "Smith & Jones" -> "Smith"
        "Smith et al." -> "Smith"
        "Smith and Jones" -> "Smith"
    """
    name = re.sub(r'\s+et\s+al\.?', '', author)
    name = re.split(r'\s+(?:&|and)\s+', name)[0]
    return name.strip()
