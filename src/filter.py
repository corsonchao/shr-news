"""Relevance gate.

"""
from __future__ import annotations


def _matches_any(text: str, terms: list[str]) -> bool:
    t = text.lower()
    return any(term.lower() in t for term in terms)


def _is_trusted(source: str) -> bool:
    return not source.startswith("GoogleNews")


def filter_relevant(items: list[dict], relevance_cfg: dict) -> list[dict]:
    shr = relevance_cfg["shr_terms"]
    domain = relevance_cfg["domain_terms"]
    kept = []
    for it in items:
        blob = f"{it['title']} {it['snippet']}"
        has_shr = _matches_any(blob, shr)
        if not has_shr:
            continue  # must be geothermal-related either way
        if _is_trusted(it["source"]):
            kept.append(it)                      # trusted feed: geothermal term is enough
        elif _matches_any(blob, domain):
            kept.append(it)                      # broad source: also needs a domain term
    return kept
