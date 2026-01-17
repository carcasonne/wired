"""Fuzzy search functionality for tracks."""

from dataclasses import dataclass

from player.core.metadata import Track


@dataclass
class SearchResult:
    """A search result with score and matched track."""
    track: Track
    index: int  # Original playlist index
    score: int  # Match score (higher = better)
    match_field: str  # Which field matched: "title", "artist", "album"


def fuzzy_search(query: str, tracks: list[Track], limit: int = 50) -> list[SearchResult]:
    """
    Search tracks using fuzzy matching.

    Searches title, artist, and album fields.
    Returns results sorted by relevance score.
    """
    if not query or not tracks:
        return []

    query_lower = query.lower()
    results: list[SearchResult] = []

    for idx, track in enumerate(tracks):
        best_score = 0
        best_field = ""

        # Check each searchable field
        for field_name, field_value in [
            ("title", track.title),
            ("artist", track.artist),
            ("album", track.album),
        ]:
            score = _score_match(query_lower, field_value.lower())
            if score > best_score:
                best_score = score
                best_field = field_name

        if best_score > 0:
            results.append(SearchResult(
                track=track,
                index=idx,
                score=best_score,
                match_field=best_field,
            ))

    # Sort by score descending
    results.sort(key=lambda r: r.score, reverse=True)

    return results[:limit]


def _score_match(query: str, text: str) -> int:
    """
    Score how well query matches text.

    Scoring:
    - Exact match: 1000
    - Starts with query: 500 + length bonus
    - Contains query: 200 + position bonus
    - Subsequence match: 100 + coverage bonus
    - No match: 0
    """
    if not query or not text:
        return 0

    # Exact match
    if query == text:
        return 1000

    # Starts with
    if text.startswith(query):
        return 500 + len(query) * 10

    # Contains
    pos = text.find(query)
    if pos >= 0:
        # Bonus for earlier position
        position_bonus = max(0, 100 - pos * 5)
        return 200 + position_bonus + len(query) * 5

    # Subsequence match (all chars appear in order)
    subseq_score = _subsequence_score(query, text)
    if subseq_score > 0:
        return 100 + subseq_score

    return 0


def _subsequence_score(query: str, text: str) -> int:
    """
    Check if query is a subsequence of text and score it.

    Returns score based on how "tight" the match is.
    """
    query_idx = 0
    text_idx = 0
    match_positions = []

    while query_idx < len(query) and text_idx < len(text):
        if query[query_idx] == text[text_idx]:
            match_positions.append(text_idx)
            query_idx += 1
        text_idx += 1

    if query_idx < len(query):
        # Not all chars matched
        return 0

    # Score based on coverage and gaps
    coverage = len(query) / len(text) * 50

    # Bonus for consecutive matches
    consecutive_bonus = 0
    for i in range(1, len(match_positions)):
        if match_positions[i] == match_positions[i-1] + 1:
            consecutive_bonus += 10

    return int(coverage + consecutive_bonus)
