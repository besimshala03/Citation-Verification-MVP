"""Bibliography parser module: match citations to bibliography entries."""

from __future__ import annotations

import re

# Matches DOI URLs in bibliography entries.
# Examples:
#   https://doi.org/10.1109/ASONAM49781.2020.9381415
#   doi:10.1109/ASONAM49781.2020.9381415
_DOI_URL_RE = re.compile(r"https?://doi\.org/\S+|doi:\s*\S+", re.IGNORECASE)

# Matches bare DOI values.
# Example: 10.1109/ASONAM49781.2020.9381415
_DOI_RE = re.compile(r"\b(10\.\d{4,}(?:\.\d+)*/\S+)")


def match_citation(author: str, year: str, bibliography_text: str | None) -> str | None:
    if not bibliography_text:
        return None

    entries = parse_entries(bibliography_text)
    surname = _extract_primary_surname(author)

    surname_pattern = re.compile(r"\b" + re.escape(surname) + r"\b", re.IGNORECASE)
    for entry in entries:
        if surname_pattern.search(entry) and year in entry:
            return entry

    return None


def parse_entries(bibliography_text: str) -> list[str]:
    entries = re.split(r"\n\s*\n", bibliography_text)
    entries = [e.strip() for e in entries if e.strip()]
    if len(entries) >= 3:
        return _heal_merged_entries(entries)

    entries = bibliography_text.split("\n")
    entries = [e.strip() for e in entries if e.strip()]
    if len(entries) >= 3:
        return _heal_merged_entries(entries)

    return _split_by_doi_boundaries(bibliography_text)


def _heal_merged_entries(entries: list[str]) -> list[str]:
    result = []
    for entry in entries:
        if len(_DOI_URL_RE.findall(entry)) > 1:
            result.extend(_split_by_doi_boundaries(entry))
        else:
            result.append(entry)
    return result


def _split_by_doi_boundaries(text: str) -> list[str]:
    doi_matches = list(_DOI_URL_RE.finditer(text))

    if not doi_matches:
        return _split_by_author_pattern(text)

    entries = []
    prev_start = 0

    for m in doi_matches:
        entry = text[prev_start : m.end()].strip()
        if entry:
            entries.append(entry)

        next_pos = m.end()
        while next_pos < len(text) and text[next_pos] in " \t\n\r":
            next_pos += 1
        prev_start = next_pos

    remaining = text[prev_start:].strip()
    if remaining:
        entries.append(remaining)

    return [e for e in entries if e.strip()]


def _split_by_author_pattern(text: str) -> list[str]:
    parts = re.split(
        r"(?<=\S)\s+(?=[A-Z][a-zA-Z\u00C0-\u017E\-\']+,\s+(?:[A-Z]\.|\w+\s+[A-Z]\.))",
        text,
    )
    return [p.strip() for p in parts if p.strip()] or [text]


def parse_entry_metadata(entry_text: str) -> dict:
    year_match = re.search(r"\b((?:19|20)\d{2})\b", entry_text)
    parsed_year = year_match.group(1) if year_match else None

    author_match = re.match(r"^([A-Z\u00C0-\u024F][a-zA-Z\u00C0-\u024F\-\']+)", entry_text)
    parsed_author = author_match.group(1) if author_match else None

    title_match = re.search(r"\(\d{4}[a-z]?\)\.\s*(.+?)\.", entry_text)
    if not title_match:
        title_match = re.search(r"\d{4}[a-z]?\.\s*(.+?)\.", entry_text)
    parsed_title = title_match.group(1).strip() if title_match else None

    return {
        "parsed_author": parsed_author,
        "parsed_year": parsed_year,
        "parsed_title": parsed_title,
    }


def extract_doi(entry_text: str) -> str | None:
    match = _DOI_RE.search(entry_text)
    if not match:
        return None
    return match.group(1).rstrip(".,;)")


def _extract_primary_surname(author: str) -> str:
    name = re.sub(r"\s+et\s+al\.?", "", author)
    name = re.split(r"\s+(?:&|and)\s+", name)[0]
    return name.strip()
