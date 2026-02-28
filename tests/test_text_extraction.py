from unittest.mock import patch

from backend.services.text_extraction import extract_pdf_text


class _Page:
    def __init__(self, text: str):
        self._text = text

    def extract_text(self):
        return self._text


class _Reader:
    def __init__(self):
        self.pages = [_Page("normal"), _Page("bad\ud800text")]


def test_extract_pdf_text_normalizes_surrogates():
    with patch("backend.services.text_extraction.PdfReader", return_value=_Reader()):
        text = extract_pdf_text(b"fake")

    assert "normal" in text
    assert "bad" in text
    assert "\ud800" not in text
