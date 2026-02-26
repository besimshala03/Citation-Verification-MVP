# Unhandled Edge Cases

This file documents known edge cases that were intentionally deferred from the MVP.
Address these in future iterations.

---

## Citation Detection

**EC-01: Year suffix disambiguation (`2020a` / `2020b`)**
When an author has multiple papers in the same year, citations like `(Smith, 2020a)` and
`(Smith, 2020b)` are not disambiguated. Currently both will match the same bibliography entries.

**EC-02: Numeric or footnote-style citations mixed in**
Documents that mix Harvard citations with numeric references (e.g., `[1]`, `¹`) may produce
false positives or missed citations in the regex pass.

**EC-03: Non-English author names**
Author names with diacritics, non-Latin characters, or unusual spacing may fail regex matching
and bibliography lookups.

**EC-04: Institutional or corporate authors**
Citations like `(WHO, 2020)` or `(European Commission, 2019)` may not match correctly since
the author string is a full organisation name, not a surname.

---

## Bibliography Matching

**EC-05: Multiple bibliography entries with the same author and year**
If a bibliography contains both `Smith (2020a)` and `Smith (2020b)`, the matcher will return
the first match and may link citations to the wrong entry.

**EC-06: Author name format mismatches**
Bibliography entries formatted as "Smith, J." vs. "John Smith" vs. "J. Smith" may not match
the in-text citation author string reliably.

---

## OpenAlex Lookup

**EC-07: Weak or wrong OpenAlex match**
For very common surnames (e.g., "Wang, 2021"), OpenAlex may return a plausible but incorrect
paper. No confidence threshold is applied to reject weak matches.

**EC-08: Bibliography entry with no extractable title**
If the bibliography entry is malformed or follows an unusual format, no meaningful title
keywords can be extracted for the OpenAlex query, reducing match quality.

**EC-09: Multiple OpenAlex results with equal relevance**
Only the top OpenAlex result is used. If the correct paper is ranked second or lower, it will
be missed entirely.

---

## Paper Retrieval

**EC-10: Open-access PDF is behind a CAPTCHA or redirect**
Some OA URLs resolve to a landing page rather than a direct PDF. The download will produce
HTML content, not extractable text.

**EC-11: PDF is scanned / image-only**
pypdf cannot extract text from scanned PDFs. The result will be an empty string with no
fallback OCR.

**EC-12: Abstract is absent or extremely short (< 50 words)**
Very short abstracts provide insufficient context for semantic matching and LLM evaluation,
likely producing UNCERTAIN results.

---

## Semantic Matching

**EC-13: Paper text is too short for chunking**
If the retrieved text is shorter than one chunk (700 chars), the entire text is treated as a
single chunk. Similarity scores may be unreliable.

**EC-14: Citing paragraph is very short (single sentence)**
A one-sentence citing paragraph may not carry enough semantic signal for reliable similarity
matching against paper chunks.

---

## LLM Evaluation

**EC-15: LLM returns malformed JSON**
If the LLM output cannot be parsed as valid JSON, the evaluation step will fail. Currently
handled by returning UNCERTAIN with an error note, but root cause may be prompt sensitivity.

**EC-16: Confidence score out of range**
The LLM may return a confidence value outside [0.0, 1.0]. No clamping is applied beyond basic
error handling.

---

## General

**EC-17: Very large documents (100+ citations)**
Processing time scales linearly with citation count. No batching, caching, or async processing
is implemented. Large documents may time out.

**EC-18: Duplicate citation text across very different contexts**
The same citation `(Smith, 2020)` appearing in wildly different paragraphs will each be
evaluated separately (by design), but they all retrieve the same paper — only the citing
paragraph changes. This is correct behaviour but may produce inconsistent labels across
occurrences.
