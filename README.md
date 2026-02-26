# Citation Verification MVP

A minimal viable product that verifies whether citations in an academic document are supported by the cited source. Upload a PDF or DOCX containing Harvard-style citations, and the system will attempt to locate the referenced papers, find relevant passages, and assess whether each citation is supported.

## How It Works

1. **Text extraction** — parses the uploaded PDF or DOCX
2. **Section splitting** — separates main text from the bibliography
3. **Citation detection** — finds Harvard-style citations via regex
4. **Bibliography matching** — links each citation to its bibliography entry
5. **Paper lookup** — searches [OpenAlex](https://openalex.org) for the cited paper
6. **Paper retrieval** — downloads open-access PDFs (or falls back to the abstract)
7. **Semantic matching** — finds the most relevant passage using sentence embeddings
8. **LLM evaluation** — classifies whether the source supports the claim

## Tech Stack

- Python 3.10+
- FastAPI + Uvicorn
- pypdf / python-docx for document parsing
- OpenAlex API for paper lookup
- sentence-transformers (`all-MiniLM-L6-v2`) for semantic similarity
- OpenAI API for LLM evaluation

## Setup

### 1. Clone the repository

```bash
git clone <repository-url>
cd Citation-Verification-MVP
```

### 2. Create a virtual environment

```bash
python -m venv venv
source venv/bin/activate  # macOS/Linux
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env .env
```

Edit `.env` and set your OpenAI API key:

```
OPENAI_API_KEY=sk-your-actual-key
MODEL_NAME=gpt-5.2
```

### 5. Run the server

```bash
uvicorn main:app --reload
```

The server starts at `http://localhost:8000`.

## API Usage

### `POST /analyze`

Upload a PDF or DOCX file for citation verification.

**Request:**

```bash
curl -X POST -F "file=@your-paper.pdf" http://localhost:8000/analyze
```

**Response:**

```json
{
  "document_name": "your-paper.pdf",
  "citations": [
    {
      "citation_text": "(Smith, 2020)",
      "author": "Smith",
      "year": "2020",
      "citing_paragraph": "The paragraph where the citation appears...",
      "bibliography_match": "Smith, J. (2020). Paper title. Journal, 1(2), 3-4.",
      "paper_found": true,
      "paper_metadata": {
        "title": "Paper title",
        "authors": ["J. Smith"],
        "year": 2020
      },
      "source_type": "pdf",
      "matched_passage": "The most relevant passage from the paper...",
      "evaluation": {
        "label": "SUPPORTS",
        "explanation": "The source provides evidence consistent with the claim.",
        "confidence": 0.85
      }
    }
  ]
}
```

### Evaluation Labels

| Label | Meaning |
|-------|---------|
| `SUPPORTS` | The source provides evidence that aligns with the claim |
| `CONTRADICTS` | The source provides evidence that opposes the claim |
| `NOT_RELEVANT` | The source does not address the topic of the claim |
| `UNCERTAIN` | Not enough information to make a determination |

### Source Types

| Type | Meaning |
|------|---------|
| `pdf` | Full paper text was retrieved from an open-access PDF |
| `abstract_only` | Only the abstract was available |
| `not_found` | Neither PDF nor abstract could be retrieved |

## Project Structure

```
main.py                  — FastAPI app and pipeline orchestration
file_processing.py       — PDF/DOCX text extraction, section splitting
citation_detection.py    — Harvard citation regex detection
bibliography_parser.py   — Citation-to-bibliography matching
paper_lookup.py          — OpenAlex API search
paper_processing.py      — PDF download and text extraction
semantic_matching.py     — Text chunking, embeddings, cosine similarity
evaluation.py            — LLM prompt construction and response parsing
```

## Known Limitations

This is an MVP focused on end-to-end functionality, not production accuracy. Known edge cases and limitations are documented in [EDGE_CASES.md](EDGE_CASES.md). Key limitations include:

- Only supports Harvard-style citations
- Year suffix disambiguation (2020a/2020b) is not handled
- Non-English author names may not match correctly
- OpenAlex may return incorrect papers for common author names
- Scanned (image-only) PDFs cannot be processed
- Large documents with many citations will be slow (sequential processing)
