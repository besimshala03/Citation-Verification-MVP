"""Citation detection module: regex-based Harvard citation extraction."""

import re
from dataclasses import dataclass


@dataclass
class CitationOccurrence:
    """A single citation occurrence in the document."""

    citation_text: str  # e.g., "(Smith, 2020)" or "Smith (2020)"
    author: str  # e.g., "Smith", "Smith & Jones", "Smith et al."
    year: str  # e.g., "2020"
    citing_paragraph: str  # the paragraph containing the citation


# Pattern for single/double/et-al author in parenthetical citations.
# Matches: (Smith, 2020), (Smith & Jones, 2019), (Smith et al., 2020)
# Also handles optional page numbers: (Smith, 2020, p. 45)
# Also handles optional year suffix: (Smith, 2020a)
_PAREN_SINGLE_RE = re.compile(
    r"\("
    r"([A-Z\u00C0-\u00D6\u00D8-\u00DE][a-zA-Z\u00C0-\u024F''-]+"  # primary author surname
    r"(?:\s+(?:&|and)\s+[A-Z\u00C0-\u00D6\u00D8-\u00DE][a-zA-Z\u00C0-\u024F''-]+)?"  # optional second author
    r"(?:\s+et\s+al\.)?"  # optional et al.
    r")"
    r",\s*"
    r"(\d{4})"  # year
    r"\w?"  # optional year suffix (a, b, etc.)
    r"(?:,\s*(?:pp?\.\s*[\d\-–]+))?"  # optional page number
    r"\)"
)

# Pattern for multi-citation brackets: (Smith, 2020; Jones, 2019)
_PAREN_MULTI_RE = re.compile(
    r"\(([^)]*\d{4}\w?\s*;\s*[^)]*\d{4}\w?[^)]*)\)"
)

# Pattern for a single citation segment within a multi-citation bracket.
_SEGMENT_RE = re.compile(
    r"([A-Z\u00C0-\u00D6\u00D8-\u00DE][a-zA-Z\u00C0-\u024F''-]+"
    r"(?:\s+(?:&|and)\s+[A-Z\u00C0-\u00D6\u00D8-\u00DE][a-zA-Z\u00C0-\u024F''-]+)?"
    r"(?:\s+et\s+al\.)?"
    r")"
    r",\s*"
    r"(\d{4})"
    r"\w?"
    r"(?:,\s*(?:pp?\.\s*[\d\-–]+))?"
)

# Pattern for narrative citations: Smith (2020), Smith and Jones (2019)
_NARRATIVE_RE = re.compile(
    r"([A-Z\u00C0-\u00D6\u00D8-\u00DE][a-zA-Z\u00C0-\u024F''-]+"
    r"(?:\s+(?:&|and)\s+[A-Z\u00C0-\u00D6\u00D8-\u00DE][a-zA-Z\u00C0-\u024F''-]+)?"
    r"(?:\s+et\s+al\.)?"
    r")"
    r"\s+\((\d{4})\w?\)"
)


def detect_citations(text: str) -> list[CitationOccurrence]:
    """Find all Harvard-style citations in the text.

    Returns one CitationOccurrence per individual citation mention.
    Not deduplicated — the same citation in different paragraphs
    produces separate entries.

    Args:
        text: The main text of the document (excluding bibliography).

    Returns:
        List of CitationOccurrence objects.
    """
    paragraphs = _split_paragraphs(text)
    results: list[CitationOccurrence] = []

    for paragraph in paragraphs:
        # Track positions already matched to avoid duplicates within a paragraph
        matched_spans: list[tuple[int, int]] = []

        # 1. Multi-citation brackets first (must be handled before single)
        for m in _PAREN_MULTI_RE.finditer(paragraph):
            matched_spans.append((m.start(), m.end()))
            inner = m.group(1)
            full_bracket = m.group(0)
            for author, year in _split_multi_citations(inner):
                results.append(CitationOccurrence(
                    citation_text=full_bracket,
                    author=author,
                    year=year,
                    citing_paragraph=paragraph,
                ))

        # 2. Single parenthetical citations
        for m in _PAREN_SINGLE_RE.finditer(paragraph):
            if _overlaps(m.start(), m.end(), matched_spans):
                continue
            matched_spans.append((m.start(), m.end()))
            results.append(CitationOccurrence(
                citation_text=m.group(0),
                author=m.group(1).strip(),
                year=m.group(2),
                citing_paragraph=paragraph,
            ))

        # 3. Narrative citations: Smith (2020)
        for m in _NARRATIVE_RE.finditer(paragraph):
            if _overlaps(m.start(), m.end(), matched_spans):
                continue
            matched_spans.append((m.start(), m.end()))
            results.append(CitationOccurrence(
                citation_text=m.group(0),
                author=m.group(1).strip(),
                year=m.group(2),
                citing_paragraph=paragraph,
            ))

    return results


def _split_paragraphs(text: str) -> list[str]:
    """Split text into paragraphs by double-newline boundaries."""
    paragraphs = re.split(r"\n\s*\n", text)
    return [p.strip() for p in paragraphs if p.strip()]


def _split_multi_citations(inner_text: str) -> list[tuple[str, str]]:
    """Split a multi-citation bracket interior into (author, year) pairs.

    Args:
        inner_text: The text inside parentheses, e.g. "Smith, 2020; Jones, 2019"

    Returns:
        List of (author, year) tuples.
    """
    segments = inner_text.split(";")
    results = []
    for segment in segments:
        segment = segment.strip()
        m = _SEGMENT_RE.search(segment)
        if m:
            results.append((m.group(1).strip(), m.group(2)))
    return results


def _overlaps(start: int, end: int, spans: list[tuple[int, int]]) -> bool:
    """Check if a span overlaps with any existing matched spans."""
    for s, e in spans:
        if start < e and end > s:
            return True
    return False
