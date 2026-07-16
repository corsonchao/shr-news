"""Cluster articles that report the SAME story, so the digest shows one blurb
with all the source links instead of near-duplicates.

WHY AN LLM: deciding whether two articles cover the same underlying story is a
judgment ("Fervo raises $100M" in three outlets = one story) that keyword
matching handles badly. We ask Claude to group them, then write one merged blurb
per group that combines what the sources collectively report.

INPUT:  the list of enriched article dicts from summarize_all (each has title,
        source, url, plain_summary, key_figures, keywords, relevance).
OUTPUT: a list of CLUSTER dicts:
    {
      "title":        headline for the merged story,
      "plain_summary":one blurb combining the sources,
      "key_figures":  merged, de-duplicated list of quantities,
      "keywords":     merged topic tags,
      "relevance":    highest relevance among members,
      "highlight":    True if relevance == high,
      "sources":      [{"name": outlet, "url": link}, ...]  # all outlets
    }
Singletons (stories only one outlet covered) come back as one-member clusters,
so downstream code treats everything uniformly.
"""
from __future__ import annotations
import json
import os
import anthropic

MODEL = "claude-haiku-4-5"

# Lazily created so importing this module (e.g. for _merge_figures during a
# site-only rebuild) does NOT require an API key. The client is only built when
# an actual LLM call is made.
_client = None


def _get_client():
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client

_CLUSTER_PROMPT = """You are given a numbered list of geothermal news articles \
(index, title, source). Group the ones that report the SAME underlying event, \
even when headlines differ in wording, angle, or detail.

GROUP TOGETHER when the core event is the same, for example:
- the same funding round or investment (e.g. all articles about a company's \
$134M raise belong in ONE group, no matter how many outlets covered it)
- the same drilling milestone, well, or test result
- the same partnership, acquisition, contract, or government action
Different framings of one event are still ONE event. A company name plus a \
dollar amount that match across articles almost always means the same story.

KEEP SEPARATE only when the events are genuinely different (different companies, \
different projects, different announcements, or clearly different dates/amounts).

Bias toward MERGING when the same company + same milestone or amount appears. \
It is better to group ten articles about one raise together than to split them.

Return ONLY a valid JSON object (no markdown, no fences) of this form:
{{"groups": [[0, 3], [1], [2, 4, 5]]}}
where each inner list contains the article indices that belong together. Every \
index from 0 to {maxindex} must appear exactly once.

ARTICLES:
{listing}"""

_MERGE_PROMPT = """These articles all cover the SAME geothermal story, from \
different outlets. Write ONE combined summary for a NON-EXPERT reader.

Return ONLY valid JSON (no markdown, no fences):
{{
  "title": "a clear headline for the combined story",
  "plain_summary": "3-4 sentences in plain language combining what the sources \
report. Define technical terms in-line. Do not repeat the same point.",
  "key_figures": ["The consolidated list of distinct numeric facts. CRITICAL: \
merge duplicates and near-duplicates into a SINGLE entry each. If one article \
says '$134 million series B funding' and another says '$134 million funding', \
output only ONE entry, the most descriptive: '$134 million Series B funding'. \
Do not list the same quantity twice with different wording. Each entry is a \
distinct fact with its unit. Only figures actually stated. Empty list if none."]
}}

ARTICLES (each: source, title, summary, figures):
{members}"""


def _llm_json(prompt: str, max_tokens: int = 600) -> dict | None:
    msg = _get_client().messages.create(
        model=MODEL, max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = "".join(b.text for b in msg.content if b.type == "text").strip()
    raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


import re as _re


def _figure_numbers(fig: str) -> frozenset:
    """Extract the set of number-like tokens (with adjacent unit) from a figure,
    so two figures sharing the same core quantity are seen as duplicates even if
    surrounding words differ. '$134 million series B funding' and '$134 million
    funding' both yield the token {'134million'}."""
    f = fig.lower().replace(",", "").replace("$", "")
    # find number optionally followed by a unit word (million/billion/m/b/k/mw/
    # ft/km/c/etc.) - capture number + immediate unit token
    toks = set()
    for m in _re.finditer(r"(\d+(?:\.\d+)?)\s*([a-z]+)?", f):
        num, unit = m.group(1), (m.group(2) or "")
        # normalize common unit synonyms
        unit = {"m": "million", "b": "billion", "k": "thousand"}.get(unit, unit)
        toks.add(num + unit)
    return frozenset(toks)


def _merge_figures(items: list[dict]) -> list[str]:
    """De-duplicate figures across articles. Two figures are duplicates if they
    share the same numeric token set (e.g. both are about '$134 million'); the
    longer, more descriptive phrasing is kept."""
    candidates: list[str] = []
    for it in items:
        for f in it.get("key_figures", []):
            f = f.strip()
            if f:
                candidates.append(f)

    kept: list[tuple[str, frozenset]] = []
    for f in sorted(candidates, key=len, reverse=True):  # longest (most descriptive) first
        nums = _figure_numbers(f)
        dup = False
        for _, kn in kept:
            # duplicate if they share numeric tokens (and this one has numbers)
            if nums and kn and nums & kn:
                dup = True
                break
        if not dup:
            kept.append((f, nums))

    kept_texts = {k for k, _ in kept}
    seen, final = set(), []
    for c in candidates:  # stable order by first appearance
        if c in kept_texts and c not in seen:
            seen.add(c); final.append(c)
    return final


def _merge_keywords(items: list[dict]) -> list[str]:
    seen, out = set(), []
    for it in items:
        for k in it.get("keywords", []):
            if k not in seen:
                seen.add(k); out.append(k)
    return out


def _best_relevance(items: list[dict]) -> str:
    order = {"high": 0, "medium": 1, "low": 2}
    return min((it.get("relevance", "low") for it in items),
               key=lambda r: order.get(r, 2))


def _one_cluster(members: list[dict]) -> dict:
    """Build a cluster dict from its member articles."""
    sources = [{"name": m["source"], "url": m["url"]} for m in members]

    if len(members) == 1:
        m = members[0]
        title = m["title"]
        summary = m.get("plain_summary", "")
        figures = m.get("key_figures", [])
    else:
        # Ask the LLM to merge the blurbs.
        listing = "\n".join(
            f'- source: {m["source"]}\n  title: {m["title"]}\n'
            f'  summary: {m.get("plain_summary","")}\n'
            f'  figures: {"; ".join(m.get("key_figures", [])) or "none"}'
            for m in members)
        merged = _llm_json(_MERGE_PROMPT.format(members=listing))
        if merged:
            title = merged.get("title", members[0]["title"])
            summary = merged.get("plain_summary", members[0].get("plain_summary", ""))
            figures = merged.get("key_figures") or _merge_figures(members)
        else:  # fallback: use first member + mechanically merged figures
            title = members[0]["title"]
            summary = members[0].get("plain_summary", "")
            figures = _merge_figures(members)

    relevance = _best_relevance(members)
    return {
        "title": title,
        "plain_summary": summary,
        "key_figures": figures,
        "keywords": _merge_keywords(members),
        "relevance": relevance,
        "highlight": relevance == "high",
        "sources": sources,
    }


def cluster_articles(enriched: list[dict]) -> list[dict]:
    """Group same-story articles and return a list of cluster dicts."""
    if not enriched:
        return []
    if len(enriched) == 1:
        return [_one_cluster(enriched)]

    listing = "\n".join(
        f'{i}: "{it["title"]}"  (source: {it["source"]})'
        for i, it in enumerate(enriched))
    result = _llm_json(_CLUSTER_PROMPT.format(maxindex=len(enriched) - 1,
                                              listing=listing))

    # Validate the grouping; fall back to all-singletons if malformed.
    groups = None
    if result and isinstance(result.get("groups"), list):
        flat = [i for g in result["groups"] for i in g]
        if sorted(flat) == list(range(len(enriched))):
            groups = result["groups"]
    if groups is None:
        groups = [[i] for i in range(len(enriched))]

    clusters = [_one_cluster([enriched[i] for i in g]) for g in groups]
    order = {"high": 0, "medium": 1, "low": 2}
    clusters.sort(key=lambda c: order.get(c["relevance"], 2))
    return clusters


def group_indices(enriched: list[dict]) -> list[list[int]]:
    """Return just the groupings (lists of indices into `enriched`) without
    merging blurbs. Used to assign persistent cluster_ids to stored articles.
    Falls back to all-singletons if the LLM response is malformed."""
    if not enriched:
        return []
    if len(enriched) == 1:
        return [[0]]
    listing = "\n".join(
        f'{i}: "{it["title"]}"  (source: {it["source"]})'
        for i, it in enumerate(enriched))
    result = _llm_json(_CLUSTER_PROMPT.format(maxindex=len(enriched) - 1,
                                              listing=listing))
    if result and isinstance(result.get("groups"), list):
        flat = [i for g in result["groups"] for i in g]
        if sorted(flat) == list(range(len(enriched))):
            return result["groups"]
    return [[i] for i in range(len(enriched))]


def make_cluster_from_records(members: list[dict]) -> dict:
    """Build a display cluster (merged blurb + all sources + merged figures)
    from stored brain records. Same shape as cluster_articles output, used by
    the website. Reuses _one_cluster which handles single vs multi merging."""
    return _one_cluster(members)
