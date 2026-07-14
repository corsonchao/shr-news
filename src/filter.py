"""Keyword relevance gate: keep items matching >=1 SHR term AND >=1 domain term."""
from __future__ import annotations


def _matches_any(text: str, terms: list[str]) -> bool:
    t = text.lower()
    return any(term.lower() in t for term in terms)


def filter_relevant(items: list[dict], relevance_cfg: dict) -> list[dict]:
    shr = relevance_cfg["shr_terms"]
    domain = relevance_cfg["domain_terms"]
    kept = []
    for it in items:
        blob = f"{it['title']} {it['snippet']}"
        if _matches_any(blob, shr) and _matches_any(blob, domain):
            kept.append(it)
    return kept
