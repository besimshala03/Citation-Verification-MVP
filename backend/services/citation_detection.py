"""Citation detection module: regex-based Harvard citation extraction."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class CitationOccurrence:
    citation_text: str
    author: str
    year: str
    citing_paragraph: str


# Examples matched:
#   (Smith, 2020)
#   (Smith & Jones, 2019)
#   (Smith et al., 2020, p. 45)
_PAREN_SINGLE_RE = re.compile(
    r"\("
    r"([A-Z\u00C0-\u00D6\u00D8-\u00DE][a-zA-Z\u00C0-\u024F''-]+"
    r"(?:\s+(?:&|and)\s+[A-Z\u00C0-\u00D6\u00D8-\u00DE][a-zA-Z\u00C0-\u024F''-]+)?"
    r"(?:\s+et\s+al\.)?"
    r")"
    r",\s*"
    r"(\d{4})"
    r"\w?"
    r"(?:,\s*(?:pp?\.\s*[\d\-–]+))?"
    r"\)"
)

# Example matched: (Smith, 2020; Jones, 2019)
_PAREN_MULTI_RE = re.compile(r"\(([^)]*\d{4}\w?\s*;\s*[^)]*\d{4}\w?[^)]*)\)")

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

# Example matched: Smith (2020)
_NARRATIVE_RE = re.compile(
    r"([A-Z\u00C0-\u00D6\u00D8-\u00DE][a-zA-Z\u00C0-\u024F''-]+"
    r"(?:\s+(?:&|and)\s+[A-Z\u00C0-\u00D6\u00D8-\u00DE][a-zA-Z\u00C0-\u024F''-]+)?"
    r"(?:\s+et\s+al\.)?"
    r")"
    r"\s+\((\d{4})\w?\)"
)


def detect_citations(text: str) -> list[CitationOccurrence]:
    paragraphs = _split_paragraphs(text)
    results: list[CitationOccurrence] = []

    for paragraph in paragraphs:
        matched_spans: list[tuple[int, int]] = []

        for m in _PAREN_MULTI_RE.finditer(paragraph):
            matched_spans.append((m.start(), m.end()))
            inner = m.group(1)
            full_bracket = m.group(0)
            for author, year in _split_multi_citations(inner):
                results.append(
                    CitationOccurrence(
                        citation_text=full_bracket,
                        author=author,
                        year=year,
                        citing_paragraph=paragraph,
                    )
                )

        for m in _PAREN_SINGLE_RE.finditer(paragraph):
            if _overlaps(m.start(), m.end(), matched_spans):
                continue
            matched_spans.append((m.start(), m.end()))
            results.append(
                CitationOccurrence(
                    citation_text=m.group(0),
                    author=m.group(1).strip(),
                    year=m.group(2),
                    citing_paragraph=paragraph,
                )
            )

        for m in _NARRATIVE_RE.finditer(paragraph):
            if _overlaps(m.start(), m.end(), matched_spans):
                continue
            matched_spans.append((m.start(), m.end()))
            results.append(
                CitationOccurrence(
                    citation_text=m.group(0),
                    author=m.group(1).strip(),
                    year=m.group(2),
                    citing_paragraph=paragraph,
                )
            )

    return results


def _split_paragraphs(text: str) -> list[str]:
    paragraphs = re.split(r"\n\s*\n", text)
    return [p.strip() for p in paragraphs if p.strip()]


def _split_multi_citations(inner_text: str) -> list[tuple[str, str]]:
    segments = inner_text.split(";")
    results = []
    for segment in segments:
        m = _SEGMENT_RE.search(segment.strip())
        if m:
            results.append((m.group(1).strip(), m.group(2)))
    return results


def _overlaps(start: int, end: int, spans: list[tuple[int, int]]) -> bool:
    for s, e in spans:
        if start < e and end > s:
            return True
    return False
