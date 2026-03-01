from backend.services.bibliography_parser import parse_entries
from backend.services.citation_detection import detect_citations


def test_citation_detection_examples():
    text = (
        "Some claim (Smith, 2020). Another by Smith (2021). "
        "Combined (Jones, 2019; Doe 2020). "
        "Rost et al. (2016) also report effects. "
        "Inline parenthetical form (Rost et al. 2016) is accepted."
    )
    citations = detect_citations(text)
    found = {(c.author, c.year) for c in citations}
    assert ("Smith", "2020") in found
    assert ("Smith", "2021") in found
    assert ("Jones", "2019") in found
    assert ("Doe", "2020") in found
    assert ("Rost et al.", "2016") in found


def test_bibliography_parse_entries_examples():
    bibliography = (
        "Smith, J. (2020). A paper. https://doi.org/10.1000/xyz\n\n"
        "Doe, A. (2021). Another paper. doi:10.1000/abc"
    )
    entries = parse_entries(bibliography)
    assert len(entries) == 2
