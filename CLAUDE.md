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
- openai (or compatible LLM client)
- python-multipart

Optional but allowed:

- pdfplumber
- tqdm

Do NOT use complex databases. In-memory processing is sufficient.

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

Detect patterns like:

- (Smith, 2020)
- (Smith & Jones, 2019)
- Smith (2020)

Use regex-based detection.

Extract:

- author string
- year (4 digits)
- full citation string
- surrounding sentence or paragraph

Return a list of citation occurrences.

---

### 5. Bibliography Parsing

Goal: match each citation to a bibliography entry.

For MVP:

Match entries containing:

- same year
- author surname present

Use simple string matching.

Return the matched bibliography text entry.

If none found, mark as "unmatched".

---

### 6. Paper Lookup via OpenAlex API

Use OpenAlex API:

https://api.openalex.org

Search using:

- author name
- year
- title keywords (if available)

Take the top result.

Extract:

- paper title
- authors
- abstract (if available)
- open access PDF URL (if available)

If no result found, mark citation as "paper_not_found".

---

### 7. Paper Text Retrieval

If an open access PDF URL is available:

- Download the PDF
- Extract text using pypdf

If not available:

- Use abstract only
- Mark source as "abstract_only"

---

### 8. Semantic Similarity Matching

Goal: find the most relevant passage in the paper for the citing paragraph.

Steps:

1. Split paper text into chunks (~500–1000 characters)
2. Compute embeddings using sentence-transformers
   Recommended model: all-MiniLM-L6-v2
3. Embed the citing paragraph
4. Compute cosine similarity
5. Select top matching chunk

---

### 9. LLM-Based Support Evaluation

Use an LLM to determine whether the paper supports the claim.

Input to LLM:

- citing paragraph
- matched paper passage (or abstract)
- citation metadata

Prompt should instruct model to classify into:

- SUPPORTS
- CONTRADICTS
- NOT_RELEVANT
- UNCERTAIN

Also request a short explanation (1–3 sentences).

Use temperature near 0.

---

### 10. Output Format

Return JSON:
{
“document_name”: “…”,
“citations”: [
{
“citation_text”: “(Smith, 2020)”,
“author”: “Smith”,
“year”: “2020”,
“citing_paragraph”: “…”,
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
    "confidence": 0.0–1.0
  }
}
]
}
If steps fail, include error fields rather than crashing.

---

## Error Handling

The system must never crash due to:

- missing bibliography
- API failures
- inaccessible PDFs
- parsing errors

Instead, include status flags in the result.

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

---

## Code Structure

Organize into modules:

- main.py (FastAPI app)
- file_processing.py
- citation_detection.py
- bibliography_parser.py
- paper_lookup.py
- paper_processing.py
- semantic_matching.py
- evaluation.py

Clean, readable, well-documented code.

---

## Performance Constraints

Designed for single-document processing.

Optimization is not required.

---

## Deliverable

A working FastAPI application that can be started with:
uvicorn main:app –reload
And tested via:
POST /analyze
---

## Implementation Priority

Correct pipeline > perfect accuracy.

End-to-end functionality is required even with heuristic methods.

---

## End of Specification
