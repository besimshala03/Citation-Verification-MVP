"""Citation Verification MVP — FastAPI application."""

import os

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile

from citation_detection import CitationOccurrence, detect_citations
from bibliography_parser import match_citation
from evaluation import EvaluationResult, evaluate_support
from file_processing import extract_text, split_sections
from paper_lookup import PaperMetadata, search_openalex
from paper_processing import retrieve_paper_text
from semantic_matching import find_best_passage

# Load environment variables from .env before anything else
load_dotenv()

app = FastAPI(title="Citation Verification MVP")


@app.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    """Accept a PDF or DOCX file and return a citation verification report."""
    # Validate file extension
    filename = file.filename or ""
    if not filename.lower().endswith((".pdf", ".docx")):
        raise HTTPException(
            status_code=400,
            detail="Unsupported file format. Only PDF and DOCX files are accepted.",
        )

    file_bytes = await file.read()

    # Step 1: Extract text
    full_text = extract_text(file_bytes, filename)
    if not full_text.strip():
        return {
            "document_name": filename,
            "citations": [],
            "warning": "Could not extract text from the document.",
        }

    # Step 2: Split into main text and bibliography
    main_text, bibliography_text = split_sections(full_text)

    # Step 3: Detect citations
    citations = detect_citations(main_text)

    # Step 4: Process each citation through the pipeline
    results = []
    for citation in citations:
        result = _process_citation(citation, bibliography_text)
        results.append(result)

    response = {"document_name": filename, "citations": results}

    if bibliography_text is None:
        response["warning"] = (
            "No bibliography/references section found in the document."
        )

    return response


def _process_citation(
    citation: CitationOccurrence, bibliography_text: str | None
) -> dict:
    """Run the full verification pipeline for a single citation.

    Wraps everything in try/except so one citation's failure
    doesn't prevent the rest from being processed.
    """
    try:
        # Match to bibliography entry
        bib_match = match_citation(
            citation.author, citation.year, bibliography_text
        )

        # Search OpenAlex
        paper = search_openalex(bib_match, citation.author, citation.year)

        # Retrieve paper text
        paper_text, source_type = retrieve_paper_text(
            paper.oa_pdf_url if paper else None,
            paper.abstract if paper else None,
        )

        # Semantic matching
        passage = find_best_passage(citation.citing_paragraph, paper_text)

        # LLM evaluation
        eval_result = evaluate_support(
            citing_paragraph=citation.citing_paragraph,
            matched_passage=passage,
            abstract=paper.abstract if paper else None,
            author=citation.author,
            year=citation.year,
            paper_title=paper.title if paper else None,
            source_type=source_type,
        )

        return _build_citation_result(
            citation, bib_match, paper, source_type, passage, eval_result
        )

    except Exception as e:
        return _build_error_result(citation, str(e))


def _build_citation_result(
    citation: CitationOccurrence,
    bib_match: str | None,
    paper: PaperMetadata | None,
    source_type: str,
    passage: str | None,
    eval_result: EvaluationResult,
) -> dict:
    """Assemble the output dict for a single citation."""
    return {
        "citation_text": citation.citation_text,
        "author": citation.author,
        "year": citation.year,
        "citing_paragraph": citation.citing_paragraph,
        "bibliography_match": bib_match,
        "paper_found": paper is not None,
        "paper_metadata": (
            {
                "title": paper.title,
                "authors": paper.authors,
                "year": paper.year,
            }
            if paper
            else None
        ),
        "source_type": source_type,
        "matched_passage": passage,
        "evaluation": {
            "label": eval_result.label,
            "explanation": eval_result.explanation,
            "confidence": eval_result.confidence,
        },
    }


def _build_error_result(citation: CitationOccurrence, error_msg: str) -> dict:
    """Build a result dict for a citation that failed during processing."""
    return {
        "citation_text": citation.citation_text,
        "author": citation.author,
        "year": citation.year,
        "citing_paragraph": citation.citing_paragraph,
        "bibliography_match": None,
        "paper_found": False,
        "paper_metadata": None,
        "source_type": "not_found",
        "matched_passage": None,
        "evaluation": {
            "label": "UNCERTAIN",
            "explanation": f"Processing error: {error_msg}",
            "confidence": 0.0,
        },
    }
