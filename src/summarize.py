"""Summarize + tag each article with Claude. Sends only TITLE + SNIPPET (never
scraped full text) — your own plain-language summary plus a link out
"""
from __future__ import annotations
import json
import os
import anthropic

MODEL = "claude-haiku-4-5"

_client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

_PROMPT = """You are summarizing geothermal energy news for a NON-EXPERT audience \
interested in superhot rock (SHR) geothermal technology.

Given an article TITLE and its TEXT (either the full article or, if that could \
not be retrieved, a short snippet), return ONLY a single valid JSON object \
(no markdown, no code fences, no commentary) with exactly these keys:

{{
  "plain_summary": "2-4 sentences in plain language for a non-expert. Define any \
technical term in-line the first time it appears. No jargon left unexplained.",
  "key_figures": ["Extract any specific NUMBERS or QUANTITIES stated in the \
text, each as a short phrase with its unit and what it measures. \
Examples: '20,000 ft drilling depth', '$100 million funding', '500 C target \
temperature', '10 MW plant capacity', '3 km well'. Only include figures that \
ACTUALLY APPEAR in the text — never invent or estimate. If none appear, use an \
empty list []."],
  "keywords": ["choose 1-6 from EXACTLY this list: {topics}"],
  "relevance": "high | medium | low  (how relevant to SHR geothermal specifically)"
}}

Do NOT copy sentences verbatim from the text — write the summary in your own \
words. If the article is not really about geothermal at all, set relevance to "low".

TITLE: {title}
TEXT: {snippet}"""


def _summarize_one(item: dict, topics: list[str]) -> dict | None:
    # Try to fetch the full article text for richer figures + summary. Falls
    # back to the RSS snippet if fetching is disallowed or fails. The full text
    # is used ONLY here and never stored (copyright-safe).
    from src.fetch_article import fetch_full_text
    full_text = fetch_full_text(item.get("url", ""))
    text_for_llm = full_text if full_text else item["snippet"]

    msg = _client.messages.create(
        model=MODEL,
        max_tokens=400,
        messages=[{
            "role": "user",
            "content": _PROMPT.format(
                topics=", ".join(topics),
                title=item["title"],
                snippet=text_for_llm,
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
    # Ensure key_figures is always a list.
    if not isinstance(data.get("key_figures"), list):
        data["key_figures"] = []
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
