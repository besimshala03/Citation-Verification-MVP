"""Export routes for verification results (CSV and PDF)."""

from __future__ import annotations

import csv
import io
import sqlite3
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from backend.auth import get_current_user
from backend.db import repository as repo
from backend.db.connection import get_db_connection

router = APIRouter()


def _gather_export_data(
    project_id: str,
    owner_id: str,
    conn: sqlite3.Connection,
) -> tuple[str, list[dict]]:
    """Gather project name, citations, and verification results for export."""
    project = repo.get_project(project_id, owner_id=owner_id, conn=conn)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    citations = repo.list_citations(project_id, conn=conn)
    rows = []
    for cit in citations:
        vr = repo.get_verification_result(cit["id"], conn=conn)
        rows.append(
            {
                "citation_text": cit["citation_text"],
                "author": cit["author"],
                "year": cit["year"],
                "citing_paragraph": cit["citing_paragraph"],
                "bibliography_match": cit.get("bibliography_match") or "",
                "label": vr["label"] if vr else "NOT_VERIFIED",
                "confidence": f"{vr['confidence']:.0%}" if vr else "",
                "explanation": vr["explanation"] if vr else "",
                "matched_passage": vr.get("matched_passage") or "" if vr else "",
            }
        )
    return project["name"], rows


@router.get("/projects/{project_id}/export/csv")
async def export_csv(
    project_id: str,
    conn: sqlite3.Connection = Depends(get_db_connection),
    current_user: dict = Depends(get_current_user),
):
    project_name, rows = _gather_export_data(project_id, current_user["id"], conn)

    if not rows:
        raise HTTPException(status_code=400, detail="No citations to export.")

    buf = io.StringIO()
    fieldnames = [
        "citation_text",
        "author",
        "year",
        "label",
        "confidence",
        "citing_paragraph",
        "bibliography_match",
        "explanation",
        "matched_passage",
    ]
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

    safe_name = "".join(c if c.isalnum() or c in " -_" else "_" for c in project_name)
    filename = f"{safe_name}_verification_results.csv"

    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/projects/{project_id}/export/pdf")
async def export_pdf(
    project_id: str,
    conn: sqlite3.Connection = Depends(get_db_connection),
    current_user: dict = Depends(get_current_user),
):
    project_name, rows = _gather_export_data(project_id, current_user["id"], conn)

    if not rows:
        raise HTTPException(status_code=400, detail="No citations to export.")

    # Build a simple text-based PDF without external dependencies.
    # Uses a minimal valid PDF structure.
    pdf_bytes = _build_simple_pdf(project_name, rows)

    safe_name = "".join(c if c.isalnum() or c in " -_" else "_" for c in project_name)
    filename = f"{safe_name}_verification_results.pdf"

    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _build_simple_pdf(project_name: str, rows: list[dict]) -> bytes:
    """Build a minimal PDF with verification results using raw PDF operators."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # Collect all text lines
    lines: list[str] = []
    lines.append(f"Citation Verification Report")
    lines.append(f"Project: {project_name}")
    lines.append(f"Generated: {timestamp}")
    lines.append(f"Total Citations: {len(rows)}")
    lines.append("")

    label_counts: dict[str, int] = {}
    for row in rows:
        label_counts[row["label"]] = label_counts.get(row["label"], 0) + 1
    lines.append("Summary:")
    for label, count in sorted(label_counts.items()):
        lines.append(f"  {label}: {count}")
    lines.append("")
    lines.append("-" * 70)

    for i, row in enumerate(rows, 1):
        lines.append("")
        lines.append(f"Citation {i}: {row['citation_text']}")
        lines.append(f"  Author: {row['author']}  Year: {row['year']}")
        lines.append(f"  Verdict: {row['label']}  Confidence: {row['confidence']}")
        if row["explanation"]:
            # Wrap explanation to ~80 chars
            exp = row["explanation"]
            while len(exp) > 75:
                cut = exp[:75].rfind(" ")
                if cut <= 0:
                    cut = 75
                lines.append(f"  {exp[:cut]}")
                exp = exp[cut:].lstrip()
            if exp:
                lines.append(f"  {exp}")
        if row["matched_passage"]:
            passage = row["matched_passage"][:200]
            lines.append(f"  Evidence: {passage}{'...' if len(row['matched_passage']) > 200 else ''}")
        lines.append("")

    # Build PDF content using raw PDF operators
    # Split into pages of ~45 lines each
    page_height = 792
    page_width = 612
    margin_top = 50
    margin_left = 50
    line_height = 14
    max_lines_per_page = (page_height - 2 * margin_top) // line_height

    pages_lines: list[list[str]] = []
    for idx in range(0, len(lines), max_lines_per_page):
        pages_lines.append(lines[idx : idx + max_lines_per_page])

    objects: list[bytes] = []
    offsets: list[int] = []

    def _pdf_escape(text: str) -> str:
        return (
            text.replace("\\", "\\\\")
            .replace("(", "\\(")
            .replace(")", "\\)")
            # Replace non-ASCII with ?
        )

    def _sanitize(text: str) -> str:
        return "".join(c if 32 <= ord(c) < 127 else "?" for c in text)

    output = io.BytesIO()
    output.write(b"%PDF-1.4\n")

    # Object 1: Catalog
    offsets.append(output.tell())
    objects.append(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
    output.write(objects[-1])

    # Object 2: Pages (placeholder, will rewrite)
    pages_obj_offset = output.tell()
    page_count = len(pages_lines)
    kids = " ".join(f"{3 + i * 2} 0 R" for i in range(page_count))
    offsets.append(output.tell())
    pages_obj = f"2 0 obj\n<< /Type /Pages /Kids [{kids}] /Count {page_count} >>\nendobj\n"
    objects.append(pages_obj.encode())
    output.write(objects[-1])

    # Font object
    font_obj_num = 3 + page_count * 2
    offsets_by_num: dict[int, int] = {1: offsets[0], 2: offsets[1]}

    # Write page + content objects
    obj_num = 3
    for page_lines in pages_lines:
        # Build content stream
        stream_lines = [
            "BT",
            f"/F1 10 Tf",
            f"{margin_left} {page_height - margin_top} Td",
            f"0 -{line_height} TL",
        ]
        for line in page_lines:
            safe = _pdf_escape(_sanitize(line))
            stream_lines.append(f"({safe}) '")
        stream_lines.append("ET")
        stream_content = "\n".join(stream_lines).encode()

        # Content stream object
        content_obj_num = obj_num + 1
        offsets_by_num[content_obj_num] = None  # placeholder

        # Page object
        offsets_by_num[obj_num] = output.tell()
        offsets.append(output.tell())
        page_obj = (
            f"{obj_num} 0 obj\n"
            f"<< /Type /Page /Parent 2 0 R "
            f"/MediaBox [0 0 {page_width} {page_height}] "
            f"/Contents {content_obj_num} 0 R "
            f"/Resources << /Font << /F1 {font_obj_num} 0 R >> >> "
            f">>\nendobj\n"
        )
        output.write(page_obj.encode())
        obj_num += 1

        # Content stream
        offsets_by_num[obj_num] = output.tell()
        offsets.append(output.tell())
        content_obj = (
            f"{obj_num} 0 obj\n"
            f"<< /Length {len(stream_content)} >>\n"
            f"stream\n"
        ).encode() + stream_content + b"\nendstream\nendobj\n"
        output.write(content_obj)
        obj_num += 1

    # Font object
    offsets_by_num[font_obj_num] = output.tell()
    offsets.append(output.tell())
    font_obj = (
        f"{font_obj_num} 0 obj\n"
        f"<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>\n"
        f"endobj\n"
    )
    output.write(font_obj.encode())

    # Cross-reference table
    total_objs = font_obj_num
    xref_offset = output.tell()
    output.write(b"xref\n")
    output.write(f"0 {total_objs + 1}\n".encode())
    output.write(b"0000000000 65535 f \n")
    for n in range(1, total_objs + 1):
        off = offsets_by_num.get(n) or 0
        output.write(f"{off:010d} 00000 n \n".encode())

    # Trailer
    output.write(
        f"trailer\n<< /Size {total_objs + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n".encode()
    )

    return output.getvalue()
