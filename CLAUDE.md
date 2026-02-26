# CLAUDE.md
## Project: Citation Verification MVP

### Goal

Build a minimal viable product (MVP) that verifies whether citations in an academic document are supported by the cited source.

The system should:

1. Accept a PDF or DOCX file containing an academic text
2. Detect in-text citations in Harvard style (Author, Year)
3. Locate matching entries in the bibliography
4. Attempt to find the referenced paper via public APIs
5. Extract text from the paper (if accessible)
6. Find the most relevant passage related to the citing paragraph
7. Use an LLM to assess whether the paper supports the claim
8. Output a structured verification report

This is NOT a production system. Focus on a functional end-to-end pipeline.

---

## Tech Stack

Language: Python 3.10+

Required libraries:

- fastapi
- uvicorn
- pypdf
- python-docx
- requests
- sentence-transformers
- numpy
- scikit-learn
- openai
- python-multipart
- python-dotenv

Optional but allowed:

- pdfplumber
- tqdm

Do NOT use complex databases. In-memory processing is sufficient.

---

## Configuration

All sensitive configuration is loaded from a `.env` file in the project root.

Required `.env` variables:

```
OPENAI_API_KEY=sk-...
MODEL_NAME=gpt-5.2
```

- `OPENAI_API_KEY`: OpenAI API key used for LLM evaluation.
- `MODEL_NAME`: The OpenAI model to use. Defaults to `gpt-5.2` but can be changed without touching code.

Load with `python-dotenv` at application startup.

---

## Application Type

A simple FastAPI backend with one upload endpoint.

No frontend required.

---

## High-Level Pipeline

Upload file → Extract text → Detect citations → Parse bibliography → Find paper → Extract paper text → Semantic matching → LLM evaluation → Return report

---

## Detailed Requirements

### 1. File Upload

Endpoint:

POST /analyze

Accept:

- multipart/form-data
- single file field named "file"
- PDF or DOCX only

Reject other formats with HTTP 400.

---

### 2. Text Extraction

#### PDF

Use pypdf (or pdfplumber fallback).

Extract full text as a single string.

#### DOCX

Use python-docx.

Extract paragraph text and join with newline.

---

### 3. Split Document Into Sections

Heuristically split into:

- Main text
- Bibliography / References section

Detect bibliography by searching for headings like:

- "References"
- "Bibliography"
- "Literature"
- "Works Cited"

Case-insensitive.

Everything after that heading is bibliography text.

If not found, return an error message in the result but continue citation detection.

---

### 4. Citation Detection (Harvard Style)

Detect the following patterns:

- `(Smith, 2020)` — single author
- `(Smith & Jones, 2019)` — two authors
- `(Smith et al., 2020)` — three or more authors abbreviated
- `Smith (2020)` — narrative citation
- `(Smith, 2020, p. 45)` — with page number (page number is stripped, not used)
- Multiple citations in one bracket: `(Smith, 2020; Jones, 2019)` — split into individual citations and process each separately

Use regex-based detection.

Extract per citation:

- author string (surname only, or "Surname et al.")
- year (4 digits)
- full citation string
- surrounding sentence or paragraph (the citing paragraph)

Year suffixes (e.g., `2020a`, `2020b`) are not validated or disambiguated in the MVP.
See EDGE_CASES.md EC-01.

Each occurrence of a citation in the document is treated as a separate entry and evaluated
independently, since the citing paragraph differs per occurrence.

Return a list of all citation occurrences (not deduplicated).

---

### 5. Bibliography Parsing

Goal: match each citation to a bibliography entry.

The bibliography is embedded in the uploaded document itself (after the References heading).

For MVP:

Match entries containing:

- same year
- author surname present

Use simple string matching.

Return the matched bibliography text entry (full line/entry as it appears in the document).
This full text is used in the OpenAlex search query in step 6, as it typically contains the
paper title.

If none found, mark as "unmatched".

---

### 6. Paper Lookup

Use a three-strategy priority chain for maximum accuracy:

**Strategy 1 — DOI-based (most accurate):**
- Extract DOI from the matched bibliography entry using regex
  (matches `https://doi.org/10.xxxx/...`, `doi:10.xxxx/...`, or bare `10.xxxx/...`)
- Query CrossRef API: `https://api.crossref.org/works/{DOI}`
  for exact paper metadata (title, authors, year, abstract)
- Query Unpaywall API: `https://api.unpaywall.org/v2/{DOI}?email=...`
  for open access PDF URL

**Strategy 2 — OpenAlex full-text search:**
- If no DOI found, use the full bibliography entry text as the search query
- URL: `https://api.openalex.org/works?search={entry_text}&per_page=1`
- The bibliography entry typically contains the paper title, giving good results

**Strategy 3 — OpenAlex author + year fallback:**
- If no bibliography entry matched, search by author name filtered by year
- Prone to wrong matches for common surnames; only used as last resort

Extract from whichever strategy succeeds:

- paper title
- authors
- abstract (if available)
- open access PDF URL (if available)

If no result found across all strategies, mark citation as "paper_not_found".

CrossRef abstracts are returned in JATS XML format — strip tags before use.
OpenAlex abstracts are returned as an inverted index — reconstruct to plain text.

---

### 7. Paper Text Retrieval

If an open access PDF URL is available:

- Download the PDF using an HTTP GET request
- Apply a timeout of 15 seconds and a maximum download size of 20 MB
- Extract text using pypdf
- If download fails (timeout, non-200 status, size exceeded, or non-PDF content), fall back
  to abstract only and mark source as "abstract_only"

If no open access PDF URL is available:

- Use abstract only
- Mark source as "abstract_only"

If neither PDF nor abstract is available:

- Mark source as "not_found"
- Skip semantic matching and LLM evaluation
- Set evaluation label to "UNCERTAIN" with explanation "No source text available"

---

### 8. Semantic Similarity Matching

Goal: find the most relevant passage in the paper for the citing paragraph.

Steps:

1. Split paper text into chunks of **700 characters** with **150 character overlap**
   - Overlap prevents relevant sentences from being split across chunk boundaries
   - If the text is shorter than one chunk, treat the entire text as a single chunk
2. Compute embeddings using sentence-transformers
   Model: `all-MiniLM-L6-v2`
3. Embed the citing paragraph
4. Compute cosine similarity between citing paragraph and all chunks
5. Select the top matching chunk as the matched passage

If the paper text is empty after retrieval, skip matching and proceed to LLM evaluation
with `matched_passage: null`. The LLM will receive only the abstract or a note that no
passage is available.

---

### 9. LLM-Based Support Evaluation

Use the OpenAI API with the model specified in `MODEL_NAME`.

Input to LLM:

- citing paragraph
- matched paper passage (or abstract if no passage; or a note if neither is available)
- citation metadata (author, year, paper title)

The LLM must return a structured JSON response. Instruct the model via system prompt to
respond ONLY with valid JSON in the following format:

```json
{
  "label": "SUPPORTS" | "CONTRADICTS" | "NOT_RELEVANT" | "UNCERTAIN",
  "explanation": "1–3 sentence explanation",
  "confidence": 0.0–1.0
}
```

- `label`: classification of whether the source supports the claim
- `explanation`: concise reasoning for the classification
- `confidence`: the model's self-assessed confidence in its classification (0.0 = no
  confidence, 1.0 = fully confident). The model determines this value itself based on the
  quality and relevance of the available evidence.

Use temperature = 0.

If the LLM response cannot be parsed as valid JSON, return:
```json
{
  "label": "UNCERTAIN",
  "explanation": "LLM response could not be parsed.",
  "confidence": 0.0
}
```

---

### 10. Output Format

Return JSON:

```json
{
  "document_name": "...",
  "citations": [
    {
      "citation_text": "(Smith, 2020)",
      "author": "Smith",
      "year": "2020",
      "citing_paragraph": "...",
      "bibliography_match": "...",
      "paper_found": true,

      "paper_metadata": {
        "title": "...",
        "authors": ["..."],
        "year": 2020
      },

      "source_type": "pdf" | "abstract_only" | "not_found",

      "matched_passage": "...",

      "evaluation": {
        "label": "SUPPORTS",
        "explanation": "...",
        "confidence": 0.0
      }
    }
  ]
}
```

If steps fail, include error fields rather than crashing.

---

## Error Handling

The system must never crash due to:

- missing bibliography
- API failures
- inaccessible or oversized PDFs
- parsing errors
- LLM response formatting errors

Instead, include status flags and fallback values in the result.

---

## Non-Goals (Out of Scope)

Do NOT implement:

- authentication
- database storage
- UI
- support for all citation styles
- paywalled paper access
- high-accuracy reference parsing
- plagiarism detection
- year suffix disambiguation (see EDGE_CASES.md EC-01)

---

## Edge Cases

Known unhandled edge cases are documented in `EDGE_CASES.md`.
Do not attempt to handle those during MVP implementation.

---

## Code Structure

Organize into modules:

- `main.py` — FastAPI app, endpoint definition, pipeline orchestration
- `file_processing.py` — PDF and DOCX text extraction, section splitting
- `citation_detection.py` — regex-based citation detection and parsing
- `bibliography_parser.py` — matching citations to bibliography entries
- `paper_lookup.py` — OpenAlex API search
- `paper_processing.py` — PDF download and text extraction
- `semantic_matching.py` — chunking, embedding, cosine similarity
- `evaluation.py` — LLM prompt construction and response parsing

Clean, readable, well-documented code.

---

## Performance Constraints

Designed for single-document processing.

Optimization is not required.

---

## Deliverable

A working FastAPI application that can be started with:

```
uvicorn main:app --reload
```

And tested via:

```
POST /analyze
```

---

## Implementation Priority

Correct pipeline > perfect accuracy.

End-to-end functionality is required even with heuristic methods.

---

## End of Specification
