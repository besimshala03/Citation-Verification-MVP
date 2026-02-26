"""Paper lookup module: find cited papers via DOI (CrossRef + Unpaywall) or OpenAlex."""

import re
from dataclasses import dataclass, field

import requests


_TIMEOUT = 15
_MAILTO = "contact@example.com"  # Used in polite-pool headers for CrossRef and Unpaywall
_HEADERS = {"User-Agent": f"CitationVerificationMVP/1.0 (mailto:{_MAILTO})"}

_CROSSREF_BASE = "https://api.crossref.org/works"
_UNPAYWALL_BASE = "https://api.unpaywall.org/v2"
_OPENALEX_BASE = "https://api.openalex.org/works"
_SEMANTIC_SCHOLAR_BASE = "https://api.semanticscholar.org/graph/v1/paper"

# Matches bare DOIs like: 10.1109/ASONAM49781.2020.9381415
# Works whether preceded by "doi:", "https://doi.org/", or just whitespace.
_DOI_RE = re.compile(r"\b(10\.\d{4,}(?:\.\d+)*/\S+)")


@dataclass
class PaperMetadata:
    """Metadata for a found paper."""

    title: str
    authors: list[str] = field(default_factory=list)
    year: int | None = None
    abstract: str | None = None
    oa_pdf_url: str | None = None


def find_paper(
    bibliography_entry: str | None, author: str, year: str
) -> PaperMetadata | None:
    """Find a cited paper using a multi-strategy priority chain.

    Strategy 1 (most accurate): Extract DOI from bibliography entry
        → CrossRef for exact metadata
        → Unpaywall for open access PDF URL

    Strategy 2 (title-based): Use full bibliography entry text as
        search query for OpenAlex (gives good results when no DOI).

    Strategy 3 (last resort): Search OpenAlex by author + year only.
        Prone to wrong matches for common surnames.

    Args:
        bibliography_entry: Full matched bibliography entry text, or None.
        author: Author string from the citation.
        year: Year string from the citation.

    Returns:
        PaperMetadata if a paper was found, None otherwise.
    """
    # Strategy 1: DOI-based (exact match)
    if bibliography_entry:
        doi = _extract_doi(bibliography_entry)
        if doi:
            paper = _lookup_crossref(doi)
            if paper:
                paper.oa_pdf_url = _get_unpaywall_url(doi)
                # Fill gaps from additional sources
                if not paper.abstract or not paper.oa_pdf_url:
                    _enrich_from_openalex(paper, doi)
                if not paper.abstract:
                    _enrich_from_semantic_scholar(paper, doi)
                return paper

    # Strategy 2: OpenAlex full-text search with bibliography entry
    if bibliography_entry:
        paper = _search_openalex_query(bibliography_entry)
        if paper:
            return paper

    # Strategy 3: OpenAlex author + year fallback
    return _search_openalex_author_year(author, year)


# ---------------------------------------------------------------------------
# DOI extraction
# ---------------------------------------------------------------------------

def _extract_doi(text: str) -> str | None:
    """Extract a DOI from bibliography entry text.

    Handles formats:
    - https://doi.org/10.1109/ASONAM49781.2020.9381415
    - doi:10.1109/ASONAM49781.2020.9381415
    - 10.1109/ASONAM49781.2020.9381415

    Returns the bare DOI string (without URL prefix), or None.
    """
    m = _DOI_RE.search(text)
    if not m:
        return None
    # Strip trailing punctuation that may have been captured by \S+
    doi = m.group(1).rstrip(".,;)")
    return doi


# ---------------------------------------------------------------------------
# Strategy 1: CrossRef + Unpaywall
# ---------------------------------------------------------------------------

def _lookup_crossref(doi: str) -> PaperMetadata | None:
    """Look up a paper by DOI via the CrossRef API."""
    try:
        response = requests.get(
            f"{_CROSSREF_BASE}/{doi}",
            params={"mailto": _MAILTO},
            headers=_HEADERS,
            timeout=_TIMEOUT,
        )
        if response.status_code != 200:
            return None
        work = response.json().get("message", {})
        if not work:
            return None
        return _parse_crossref_work(work)
    except Exception:
        return None


def _parse_crossref_work(work: dict) -> PaperMetadata:
    """Parse a CrossRef work object into PaperMetadata."""
    titles = work.get("title", [])
    title = titles[0] if titles else "Unknown"

    authors = []
    for author in work.get("author", []):
        given = author.get("given", "")
        family = author.get("family", "")
        name = f"{given} {family}".strip() if given else family
        if name:
            authors.append(name)

    year = None
    for date_field in ("published", "published-print", "published-online"):
        date_parts = work.get(date_field, {}).get("date-parts", [[]])
        if date_parts and date_parts[0]:
            year = date_parts[0][0]
            break

    # CrossRef abstracts often contain JATS XML tags — strip them
    abstract_raw = work.get("abstract", "")
    abstract = _strip_xml_tags(abstract_raw) if abstract_raw else None

    return PaperMetadata(title=title, authors=authors, year=year, abstract=abstract)


def _strip_xml_tags(text: str) -> str:
    """Remove XML/HTML tags (CrossRef abstracts use JATS XML format)."""
    return re.sub(r"<[^>]+>", "", text).strip()


def _get_unpaywall_url(doi: str) -> str | None:
    """Get the best open access PDF URL for a DOI from Unpaywall."""
    try:
        response = requests.get(
            f"{_UNPAYWALL_BASE}/{doi}",
            params={"email": _MAILTO},
            headers=_HEADERS,
            timeout=_TIMEOUT,
        )
        if response.status_code != 200:
            return None
        best = response.json().get("best_oa_location") or {}
        return best.get("url_for_pdf")
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Strategy 2 & 3: OpenAlex
# ---------------------------------------------------------------------------

def _search_openalex_query(query: str) -> PaperMetadata | None:
    """Search OpenAlex with a free-text query (bibliography entry text)."""
    try:
        response = requests.get(
            _OPENALEX_BASE,
            params={"search": query, "per_page": 1},
            headers=_HEADERS,
            timeout=_TIMEOUT,
        )
        if response.status_code != 200:
            return None
        results = response.json().get("results", [])
        return _parse_openalex_work(results[0]) if results else None
    except Exception:
        return None


def _search_openalex_author_year(author: str, year: str) -> PaperMetadata | None:
    """Search OpenAlex by author name filtered by publication year."""
    try:
        response = requests.get(
            _OPENALEX_BASE,
            params={
                "search": author,
                "filter": f"publication_year:{year}",
                "per_page": 1,
            },
            headers=_HEADERS,
            timeout=_TIMEOUT,
        )
        if response.status_code != 200:
            return None
        results = response.json().get("results", [])
        return _parse_openalex_work(results[0]) if results else None
    except Exception:
        return None


def _parse_openalex_work(work: dict) -> PaperMetadata:
    """Parse a single OpenAlex work object into PaperMetadata."""
    title = work.get("title") or work.get("display_name") or "Unknown"

    authors = []
    for authorship in work.get("authorships", []):
        name = authorship.get("author", {}).get("display_name")
        if name:
            authors.append(name)

    year = work.get("publication_year")
    abstract = _reconstruct_abstract(work.get("abstract_inverted_index"))

    oa_pdf_url = None
    oa = work.get("open_access", {})
    if oa:
        oa_pdf_url = oa.get("oa_url")

    return PaperMetadata(title=title, authors=authors, year=year, abstract=abstract, oa_pdf_url=oa_pdf_url)


# ---------------------------------------------------------------------------
# Enrichment: fill missing abstract / OA PDF from additional APIs
# ---------------------------------------------------------------------------

def _enrich_from_openalex(paper: PaperMetadata, doi: str) -> None:
    """Try to fill missing abstract and OA PDF URL from OpenAlex by DOI."""
    try:
        response = requests.get(
            f"{_OPENALEX_BASE}/doi:{doi}",
            headers=_HEADERS,
            timeout=_TIMEOUT,
        )
        if response.status_code != 200:
            return
        work = response.json()
        if not paper.abstract:
            paper.abstract = _reconstruct_abstract(work.get("abstract_inverted_index"))
        if not paper.oa_pdf_url:
            oa = work.get("open_access", {})
            if oa:
                paper.oa_pdf_url = oa.get("oa_url")
    except Exception:
        pass


def _enrich_from_semantic_scholar(paper: PaperMetadata, doi: str) -> None:
    """Try to fill missing abstract from Semantic Scholar by DOI."""
    try:
        response = requests.get(
            f"{_SEMANTIC_SCHOLAR_BASE}/DOI:{doi}",
            params={"fields": "abstract,openAccessPdf"},
            timeout=_TIMEOUT,
        )
        if response.status_code != 200:
            return
        data = response.json()
        if not paper.abstract and data.get("abstract"):
            paper.abstract = data["abstract"]
        if not paper.oa_pdf_url:
            oa_pdf = data.get("openAccessPdf") or {}
            if oa_pdf.get("url"):
                paper.oa_pdf_url = oa_pdf["url"]
    except Exception:
        pass


def _reconstruct_abstract(inverted_index: dict | None) -> str | None:
    """Reconstruct plain-text abstract from OpenAlex inverted index format."""
    if not inverted_index:
        return None
    word_positions: list[tuple[int, str]] = []
    for word, positions in inverted_index.items():
        for pos in positions:
            word_positions.append((pos, word))
    word_positions.sort(key=lambda x: x[0])
    return " ".join(word for _, word in word_positions)
