"""Deprecated semantic matching module.

This module is kept temporarily for backward compatibility and will be removed
in a follow-up cleanup after migration to the full-LLM verification approach.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)
logger.warning("semantic_matching module is deprecated and not used in active pipeline")


def find_best_passage(citing_paragraph: str, paper_text: str | None) -> str | None:
    _ = citing_paragraph
    _ = paper_text
    return None
