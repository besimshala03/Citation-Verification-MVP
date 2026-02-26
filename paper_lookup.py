"""Paper lookup module: search OpenAlex for cited papers."""

from dataclasses import dataclass, field

import requests


_OPENALEX_BASE = "https://api.openalex.org/works"
_USER_AGENT = "CitationVerificationMVP/1.0 (mailto:contact@example.com)"
_TIMEOUT = 15


@dataclass
class PaperMetadata:
    """Metadata for a paper found via OpenAlex."""

    title: str
    authors: list[str] = field(default_factory=list)
    year: int | None = None
    abstract: str | None = None
    oa_pdf_url: str | None = None


def search_openalex(
    bibliography_entry: str | None, author: str, year: str
) -> PaperMetadata | None:
    """Search OpenAlex for a cited paper.

    Primary strategy: use the full bibliography entry text as the search query
    (it typically contains the paper title, giving high match quality).
    Fallback: search by author name filtered by publication year.

    Args:
        bibliography_entry: Full matched bibliography entry text, or None.
        author: Author string from the citation.
        year: Year string from the citation.

    Returns:
        PaperMetadata if a paper was found, None otherwise.
    """
    # Primary: search with bibliography entry text
    if bibliography_entry:
        result = _search_by_query(bibliography_entry)
        if result:
            return result

    # Fallback: search by author + year filter
    result = _search_by_author_year(author, year)
    return result


def _search_by_query(query: str) -> PaperMetadata | None:
    """Search OpenAlex with a free-text query."""
    try:
        response = requests.get(
            _OPENALEX_BASE,
            params={"search": query, "per_page": 1},
            headers={"User-Agent": _USER_AGENT},
            timeout=_TIMEOUT,
        )
        if response.status_code != 200:
            return None
        data = response.json()
        results = data.get("results", [])
        if not results:
            return None
        return _parse_work(results[0])
    except Exception:
        return None


def _search_by_author_year(author: str, year: str) -> PaperMetadata | None:
    """Search OpenAlex by author name filtered by publication year."""
    try:
        response = requests.get(
            _OPENALEX_BASE,
            params={
                "search": author,
                "filter": f"publication_year:{year}",
                "per_page": 1,
            },
            headers={"User-Agent": _USER_AGENT},
            timeout=_TIMEOUT,
        )
        if response.status_code != 200:
            return None
        data = response.json()
        results = data.get("results", [])
        if not results:
            return None
        return _parse_work(results[0])
    except Exception:
        return None


def _parse_work(work: dict) -> PaperMetadata:
    """Parse a single OpenAlex work object into PaperMetadata."""
    title = work.get("title") or work.get("display_name") or "Unknown"

    authors = []
    for authorship in work.get("authorships", []):
        author_obj = authorship.get("author", {})
        name = author_obj.get("display_name")
        if name:
            authors.append(name)

    year = work.get("publication_year")

    abstract = _reconstruct_abstract(work.get("abstract_inverted_index"))

    oa_pdf_url = None
    oa = work.get("open_access", {})
    if oa:
        oa_pdf_url = oa.get("oa_url")

    return PaperMetadata(
        title=title,
        authors=authors,
        year=year,
        abstract=abstract,
        oa_pdf_url=oa_pdf_url,
    )


def _reconstruct_abstract(inverted_index: dict | None) -> str | None:
    """Reconstruct plain-text abstract from OpenAlex inverted index format.

    OpenAlex stores abstracts as {"word": [position1, position2], ...}.
    This function inverts the index back to ordered plain text.
    """
    if not inverted_index:
        return None

    word_positions: list[tuple[int, str]] = []
    for word, positions in inverted_index.items():
        for pos in positions:
            word_positions.append((pos, word))

    word_positions.sort(key=lambda x: x[0])
    return " ".join(word for _, word in word_positions)
