"""Tests for retained public literature utilities."""

from pathlib import Path
from unittest.mock import patch

from researchclaw.literature.cache import get_cached, put_cache
from researchclaw.literature.models import Paper
from researchclaw.literature.search import search_papers


def test_literature_cache_stays_in_explicit_workspace(tmp_path: Path) -> None:
    cache = tmp_path / "cache"
    papers = [{"paper_id": "p1", "title": "Measured result"}]

    put_cache("query", "openalex", 5, papers, cache_base=cache)

    assert get_cached("query", "openalex", 5, cache_base=cache) == papers
    assert len(list(cache.glob("*.json"))) == 1


def test_multi_source_search_deduplicates_real_metadata() -> None:
    low = Paper(
        paper_id="openalex-1",
        title="Direct Neighbor",
        doi="10.1/example",
        citation_count=2,
    )
    high = Paper(
        paper_id="s2-1",
        title="Direct Neighbor",
        doi="10.1/example",
        citation_count=20,
    )

    def cache_get(_query: str, _source: str, _limit: int) -> None:
        return None

    def cache_put(
        _query: str,
        _source: str,
        _limit: int,
        _papers: list[dict[str, object]],
    ) -> None:
        return None

    with (
        patch("researchclaw.literature.search.search_openalex", return_value=[low]),
        patch(
            "researchclaw.literature.search.search_semantic_scholar",
            return_value=[high],
        ),
        patch(
            "researchclaw.literature.search._cache_api",
            return_value=(cache_get, cache_put),
        ),
        patch("researchclaw.literature.search.time.sleep"),
    ):
        result = search_papers(
            "algorithm gap",
            sources=("openalex", "semantic_scholar"),
        )

    assert result == [high]
