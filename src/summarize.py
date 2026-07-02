"""Summarize + tag each article with Claude. Sends only TITLE + SNIPPET (never
scraped full text) — your own plain-language summary plus a link out.

Model strings verified against platform.claude.com Models overview + anthropics/
skills models.md (2026): claude-haiku-4-5 (cheap default), claude-sonnet-4-6
(richer), claude-opus-4-8 (most capable). Confirm live IDs at
https://platform.claude.com/docs/en/about-claude/models/overview if a call 404s.
"""
from __future__ import annotations
import json
import os
import anthropic

MODEL = "claude-haiku-4-5"

_client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

_PROMPT = """You are summarizing geothermal energy news for a NON-EXPERT audience \
interested in superhot rock (SHR) geothermal technology.

Given an article TITLE and SNIPPET, return ONLY a single valid JSON object \
(no markdown, no code fences, no commentary) with exactly these keys:

{{
  "plain_summary": "2-3 sentences in plain language. Define any technical term \
in-line the first time it appears. No jargon left unexplained.",
  "keywords": ["choose 1-6 from EXACTLY this list: {topics}"],
  "relevance": "high | medium | low  (how relevant to SHR geothermal specifically)"
}}

If the article is not really about geothermal at all, set relevance to "low".

TITLE: {title}
SNIPPET: {snippet}"""


def _summarize_one(item: dict, topics: list[str]) -> dict | None:
    msg = _client.messages.create(
        model=MODEL,
        max_tokens=400,
        messages=[{
            "role": "user",
            "content": _PROMPT.format(
                topics=", ".join(topics),
                title=item["title"],
                snippet=item["snippet"],
            ),
        }],
    )
    raw = "".join(b.text for b in msg.content if b.type == "text").strip()
    raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    # Keep only topics from the canonical list (guards against stray tags).
    data["keywords"] = [k for k in data.get("keywords", []) if k in topics]
    return {**item, **data}


def summarize_all(items: list[dict], topics: list[str], drop_low: bool = True) -> list[dict]:
    out = []
    for it in items:
        enriched = _summarize_one(it, topics)
        if enriched is None:
            continue
        if drop_low and enriched.get("relevance") == "low":
            continue
        out.append(enriched)
    order = {"high": 0, "medium": 1, "low": 2}
    out.sort(key=lambda x: order.get(x.get("relevance", "low"), 2))
    return out
