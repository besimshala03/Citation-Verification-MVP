from backend.models.schemas import VerificationResultSchema


def test_verification_result_allows_not_found_source_type():
    payload = {
        "citation_text": "(Smith, 2020)",
        "author": "Smith",
        "year": "2020",
        "citing_paragraph": "A paragraph",
        "bibliography_match": None,
        "paper_found": False,
        "paper_metadata": None,
        "source_type": "not_found",
        "matched_passage": None,
        "evaluation": {
            "label": "UNCERTAIN",
            "explanation": "No source",
            "confidence": 0.0,
        },
    }
    parsed = VerificationResultSchema.model_validate(payload)
    assert parsed.source_type == "not_found"
