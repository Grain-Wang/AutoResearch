"""Real literature search and citation management for ResearchClaw.

Provides API clients for OpenAlex, Semantic Scholar, and arXiv, plus unified
search, deduplication, novelty checks, and citation verification.
"""

from researchclaw.literature.models import Author, Paper
from researchclaw.literature.search import search_papers
from researchclaw.literature.verify import (
    CitationResult,
    VerificationReport,
    VerifyStatus,
    verify_citations,
)

__all__ = [
    "Author",
    "CitationResult",
    "Paper",
    "VerificationReport",
    "VerifyStatus",
    "search_papers",
    "verify_citations",
]
