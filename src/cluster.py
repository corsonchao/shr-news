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
_client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

_CLUSTER_PROMPT = """You are given a numbered list of geothermal news articles \
(index, title, source). Group together the ones that report the SAME underlying \
story or event (e.g. the same funding round, the same drilling milestone, the \
same partnership), even if the wording differs. Articles about DIFFERENT stories \
must stay in separate groups. When unsure, keep them separate.

Return ONLY a valid JSON object (no markdown, no fences) of this form:
{{"groups": [[0, 3], [1], [2, 4, 5]]}}
where each inner list contains the article indices that belong together. Every \
index from 0 to {maxindex} must appear exactly once.

ARTICLES:
{listing}"""

_MERGE_PROMPT = """These articles all cover the same geothermal story, from \
different outlets. Write ONE combined summary for a NON-EXPERT reader.

Return ONLY valid JSON (no markdown, no fences):
{{
  "title": "a clear headline for the combined story",
  "plain_summary": "3-4 sentences in plain language combining what the sources \
report. Define technical terms in-line. Do not repeat the same point.",
  "key_figures": ["merged list of specific numbers/quantities with units that \
appear across these articles, de-duplicated. Only figures actually stated. \
Empty list if none."]
}}

ARTICLES (each: source, title, summary, figures):
{members}"""


def _llm_json(prompt: str, max_tokens: int = 600) -> dict | None:
    msg = _client.messages.create(
        model=MODEL, max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = "".join(b.text for b in msg.content if b.type == "text").strip()
    raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def _merge_figures(items: list[dict]) -> list[str]:
    seen, out = set(), []
    for it in items:
        for f in it.get("key_figures", []):
            k = f.strip().lower()
            if k and k not in seen:
                seen.add(k); out.append(f.strip())
    return out


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
