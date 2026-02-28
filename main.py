"""Citation Verification MVP — FastAPI application with project-based workflow."""

from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

import database as db
from bibliography_parser import (
    match_citation,
    parse_entries,
    parse_entry_metadata,
)
from citation_detection import detect_citations
from evaluation import evaluate_support
from file_processing import extract_text, split_sections
from paper_processing import extract_pdf_text

# Load environment variables from .env before anything else
load_dotenv()


# ---------------------------------------------------------------------------
# App lifecycle
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(application: FastAPI):
    """Initialize the database on startup."""
    db.init_db()
    yield


app = FastAPI(title="Citation Verification MVP", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class CreateProjectRequest(BaseModel):
    name: str


class VerifyCitationRequest(BaseModel):
    citation_id: int


# =========================================================================
# PROJECTS
# =========================================================================

@app.post("/projects")
async def create_project(req: CreateProjectRequest):
    """Create a new project."""
    project = db.create_project(req.name)
    return project


@app.get("/projects")
async def list_projects():
    """List all projects with summary stats."""
    projects = db.list_projects()
    return {"projects": projects}


@app.get("/projects/{project_id}")
async def get_project(project_id: str):
    """Get project details including document, references, and citation count."""
    project = db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    document = db.get_document(project_id)
    references = db.list_reference_entries(project_id)
    citations = db.list_citations(project_id)

    return {
        "id": project["id"],
        "name": project["name"],
        "created_at": project["created_at"],
        "updated_at": project["updated_at"],
        "document": (
            {"id": document["id"], "filename": document["filename"]}
            if document
            else None
        ),
        "reference_entries": references,
        "citation_count": len(citations),
        "warning": None,
    }


@app.delete("/projects/{project_id}")
async def delete_project(project_id: str):
    """Delete a project and all associated data."""
    deleted = db.delete_project(project_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Project not found.")
    return {"deleted": True}


# =========================================================================
# DOCUMENT UPLOAD
# =========================================================================

@app.post("/projects/{project_id}/document")
async def upload_document(project_id: str, file: UploadFile = File(...)):
    """Upload the main document for a project.

    Parses bibliography, detects citations, and creates reference entries.
    """
    project = db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    filename = file.filename or ""
    if not filename.lower().endswith((".pdf", ".docx")):
        raise HTTPException(
            status_code=400,
            detail="Unsupported file format. Only PDF and DOCX files are accepted.",
        )

    file_bytes = await file.read()
    full_text = extract_text(file_bytes, filename)
    if not full_text.strip():
        raise HTTPException(
            status_code=400, detail="Could not extract text from the document."
        )

    main_text, bibliography_text = split_sections(full_text)

    # Save document to DB + disk
    doc = db.save_document(
        project_id=project_id,
        filename=filename,
        file_bytes=file_bytes,
        full_text=full_text,
        main_text=main_text,
        bibliography_text=bibliography_text,
    )

    # Parse bibliography into reference entries
    warning = None
    ref_entries_created = []
    if bibliography_text:
        raw_entries = parse_entries(bibliography_text)
        entries_with_metadata = []
        for entry_text in raw_entries:
            meta = parse_entry_metadata(entry_text)
            entries_with_metadata.append({
                "entry_text": entry_text,
                **meta,
            })
        ref_entries_created = db.create_reference_entries(
            project_id, doc["id"], entries_with_metadata
        )
    else:
        warning = "No bibliography/references section found in the document."

    # Detect citations and match to reference entries
    citations = detect_citations(main_text)
    citation_dicts = []
    for cit in citations:
        # Match citation to a reference entry
        matched_entry_id = None
        matched_entry_text = None
        for ref_entry in ref_entries_created:
            # Use simple surname + year matching against entry text
            bib_match = match_citation(
                cit.author, cit.year, ref_entry["entry_text"]
            )
            if bib_match:
                matched_entry_id = ref_entry["id"]
                matched_entry_text = ref_entry["entry_text"]
                break

        citation_dicts.append({
            "citation_text": cit.citation_text,
            "author": cit.author,
            "year": cit.year,
            "citing_paragraph": cit.citing_paragraph,
            "reference_entry_id": matched_entry_id,
            "bibliography_match": matched_entry_text,
        })

    saved_citations = db.save_citations(project_id, doc["id"], citation_dicts)

    response = {
        "document_id": doc["id"],
        "filename": filename,
        "citation_count": len(saved_citations),
        "reference_entries": ref_entries_created,
        "warning": warning,
    }
    return response


@app.get("/projects/{project_id}/document/file")
async def serve_document(project_id: str):
    """Serve the uploaded document for PDF rendering."""
    doc = db.get_document(project_id)
    if not doc:
        raise HTTPException(status_code=404, detail="No document uploaded.")

    disk_path = Path(doc["disk_path"])
    if not disk_path.exists():
        raise HTTPException(status_code=404, detail="Document file missing from disk.")

    file_bytes = disk_path.read_bytes()
    filename = doc["filename"]
    media_type = (
        "application/pdf"
        if filename.lower().endswith(".pdf")
        else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    return Response(content=file_bytes, media_type=media_type)


# =========================================================================
# REFERENCES
# =========================================================================

@app.get("/projects/{project_id}/references")
async def list_references(project_id: str):
    """List all reference entries for a project."""
    project = db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    references = db.list_reference_entries(project_id)
    return {"references": references}


@app.post("/projects/{project_id}/references/{entry_id}/paper")
async def upload_reference_paper(
    project_id: str, entry_id: int, file: UploadFile = File(...)
):
    """Upload a PDF for a specific reference entry."""
    project = db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    entry = db.get_reference_entry(entry_id)
    if not entry or entry["project_id"] != project_id:
        raise HTTPException(status_code=404, detail="Reference entry not found.")

    filename = file.filename or ""
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400, detail="Only PDF files are accepted for reference papers."
        )

    file_bytes = await file.read()

    # Extract text from the reference paper
    extracted_text = extract_pdf_text(file_bytes)

    result = db.save_reference_paper(
        reference_entry_id=entry_id,
        project_id=project_id,
        filename=filename,
        file_bytes=file_bytes,
        extracted_text=extracted_text,
    )
    return result


@app.delete("/projects/{project_id}/references/{entry_id}/paper")
async def delete_reference_paper(project_id: str, entry_id: int):
    """Remove an uploaded reference paper."""
    entry = db.get_reference_entry(entry_id)
    if not entry or entry["project_id"] != project_id:
        raise HTTPException(status_code=404, detail="Reference entry not found.")

    deleted = db.delete_reference_paper(entry_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="No paper uploaded for this reference.")
    return {"deleted": True}


@app.get("/projects/{project_id}/references/{entry_id}/paper/file")
async def serve_reference_paper(project_id: str, entry_id: int):
    """Serve an uploaded reference paper PDF."""
    paper = db.get_reference_paper(entry_id)
    if not paper or paper["project_id"] != project_id:
        raise HTTPException(status_code=404, detail="Reference paper not found.")

    disk_path = Path(paper["disk_path"])
    if not disk_path.exists():
        raise HTTPException(status_code=404, detail="Paper file missing from disk.")

    file_bytes = disk_path.read_bytes()
    return Response(content=file_bytes, media_type="application/pdf")


# =========================================================================
# CITATIONS & VERIFICATION
# =========================================================================

@app.get("/projects/{project_id}/citations")
async def get_citations(project_id: str):
    """Get all citations for a project."""
    project = db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    citations = db.list_citations(project_id)
    return {"citations": citations}


@app.post("/projects/{project_id}/verify-citation")
async def verify_citation(project_id: str, req: VerifyCitationRequest):
    """Verify a single citation on demand.

    Uses the locally uploaded reference paper for verification.
    """
    project = db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    citations = db.list_citations(project_id)
    citation = None
    for c in citations:
        if c["id"] == req.citation_id:
            citation = c
            break

    if not citation:
        raise HTTPException(status_code=404, detail="Citation not found.")

    try:
        result = _process_citation_local(citation)

        # Save verification result to DB
        db.save_verification_result(
            citation_id=citation["id"],
            project_id=project_id,
            result={
                "source_type": result["source_type"],
                "matched_passage": result["matched_passage"],
                "label": result["evaluation"]["label"],
                "explanation": result["evaluation"]["explanation"],
                "confidence": result["evaluation"]["confidence"],
            },
        )

        return result

    except Exception as e:
        error_result = _build_error_result(citation, str(e))
        return error_result


# ---------------------------------------------------------------------------
# Pipeline helpers
# ---------------------------------------------------------------------------

def _process_citation_local(citation: dict) -> dict:
    """Run verification for a single citation using locally uploaded paper text."""
    ref_entry_id = citation.get("reference_entry_id")

    # No bibliography match
    if not ref_entry_id:
        return _build_result(
            citation,
            source_type="not_uploaded",
            passage=None,
            label="UNCERTAIN",
            explanation="No bibliography match found for this citation.",
            confidence=0.0,
        )

    # Check if reference paper is uploaded
    ref_paper = db.get_reference_paper(ref_entry_id)
    if not ref_paper:
        return _build_result(
            citation,
            source_type="not_uploaded",
            passage=None,
            label="UNCERTAIN",
            explanation="Reference paper not yet uploaded. Upload the PDF for this reference to enable verification.",
            confidence=0.0,
        )

    paper_text = ref_paper.get("extracted_text", "")
    if not paper_text or not paper_text.strip():
        return _build_result(
            citation,
            source_type="pdf",
            passage=None,
            label="UNCERTAIN",
            explanation="Could not extract readable text from the uploaded PDF.",
            confidence=0.0,
        )

    # LLM evaluation — send full paper text so the LLM can search for
    # the relevant passage itself (far more accurate than embedding-based
    # matching, especially for cross-language documents).
    eval_result = evaluate_support(
        citing_paragraph=citation["citing_paragraph"],
        matched_passage=None,
        abstract=None,
        author=citation["author"],
        year=citation["year"],
        paper_title=ref_paper.get("filename", "Unknown"),
        source_type="pdf",
        paper_text=paper_text,
    )

    # Use the passage the LLM identified as most relevant
    passage = eval_result.relevant_passage

    return _build_result(
        citation,
        source_type="pdf",
        passage=passage,
        label=eval_result.label,
        explanation=eval_result.explanation,
        confidence=eval_result.confidence,
        paper_filename=ref_paper.get("filename"),
    )


def _build_result(
    citation: dict,
    source_type: str,
    passage: str | None,
    label: str,
    explanation: str,
    confidence: float,
    paper_filename: str | None = None,
) -> dict:
    """Assemble the verification result dict."""
    return {
        "citation_text": citation["citation_text"],
        "author": citation["author"],
        "year": citation["year"],
        "citing_paragraph": citation["citing_paragraph"],
        "bibliography_match": citation.get("bibliography_match"),
        "paper_found": source_type == "pdf",
        "paper_metadata": (
            {
                "title": paper_filename or "Uploaded Paper",
                "authors": [],
                "year": int(citation["year"]) if citation["year"].isdigit() else None,
            }
            if source_type == "pdf"
            else None
        ),
        "source_type": source_type,
        "matched_passage": passage,
        "evaluation": {
            "label": label,
            "explanation": explanation,
            "confidence": confidence,
        },
    }


def _build_error_result(citation: dict, error_msg: str) -> dict:
    """Build a result dict for a citation that failed during processing."""
    return {
        "citation_text": citation["citation_text"],
        "author": citation["author"],
        "year": citation["year"],
        "citing_paragraph": citation["citing_paragraph"],
        "bibliography_match": citation.get("bibliography_match"),
        "paper_found": False,
        "paper_metadata": None,
        "source_type": "not_uploaded",
        "matched_passage": None,
        "evaluation": {
            "label": "UNCERTAIN",
            "explanation": f"Processing error: {error_msg}",
            "confidence": 0.0,
        },
    }
