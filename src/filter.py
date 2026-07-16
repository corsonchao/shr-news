"""Relevance gate (two-tier).

TRUSTED FEEDS (curated RSS sources) pass on a geothermal/superhot term alone —
they're dedicated outlets and RSS snippets are too short to reliably contain a
narrow domain keyword.

BROAD SOURCES (Google News search results, flagged from_broad_search in
collect.py) keep the stricter rule: must match a geothermal term AND a domain
term, because broad searches are where the noise is.
"""
from __future__ import annotations


def _matches_any(text: str, terms: list[str]) -> bool:
    t = text.lower()
    return any(term.lower() in t for term in terms)


def _is_trusted(item: dict) -> bool:
    """Trusted = from a curated RSS feed, not a broad Google News search."""
    return not item.get("from_broad_search", False)


def filter_relevant(items: list[dict], relevance_cfg: dict) -> list[dict]:
    shr = relevance_cfg["shr_terms"]
    domain = relevance_cfg["domain_terms"]
    kept = []
    for it in items:
        blob = f"{it['title']} {it['snippet']}"
        if not _matches_any(blob, shr):
            continue
        if _is_trusted(it):
            kept.append(it)
        elif _matches_any(blob, domain):
            kept.append(it)
    return kept
