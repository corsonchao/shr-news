"""The 'geothermal brain': a persistent knowledge base kept as files in the repo.

WHY FILES (Option A): the daily job already reads/writes this repo to update the
website, so the brain lives in the same place — no second service, no extra auth,
and every day's additions are a git commit you can inspect and roll back.

LAYOUT (all under knowledge/):
    knowledge/articles.json      -> the full corpus: every article ever kept,
                                    keyed by URL so we never store one twice.
    knowledge/by_topic.json      -> {topic: [article_ids]} index for topic pages.
    knowledge/by_date.json       -> {YYYY-MM-DD: [article_ids]} index for date pages.

Each article record:
    {
      "id", "url", "title", "source", "published", "date_added",
      "plain_summary", "keywords" [topics], "relevance", "highlight" (bool)
    }

DESIGNED FOR A SEMANTIC UPGRADE LATER (Option C): articles.json is a flat,
embeddable corpus. To add meaning-based search later, embed each record's
title+plain_summary and store vectors alongside — no restructuring needed.

OPTIONAL ONEDRIVE MIRROR: if you ever want this browsable in OneDrive, add a
final pipeline step that copies knowledge/*.json (or a rendered markdown export)
to OneDrive via the Microsoft Graph API. Keep the repo as the source of truth;
treat OneDrive as a read-only mirror. Not built here — it needs Graph OAuth setup.
"""
from __future__ import annotations
import hashlib
import json
import os
import datetime as dt

KB_DIR = "knowledge"
ARTICLES = os.path.join(KB_DIR, "articles.json")
BY_TOPIC = os.path.join(KB_DIR, "by_topic.json")
BY_DATE = os.path.join(KB_DIR, "by_date.json")


def _load(path: str, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def _save(path: str, data) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _article_id(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]


def load_known_urls() -> set[str]:
    """URLs already in the brain — used to skip re-summarizing old news."""
    return set(_load(ARTICLES, {}).keys())


def add_articles(enriched: list[dict]) -> list[dict]:
    """Merge today's summarized articles into the brain. Returns the ones that
    were actually new (so the email/website show only fresh items)."""
    articles = _load(ARTICLES, {})            # keyed by URL
    by_topic = _load(BY_TOPIC, {})
    by_date = _load(BY_DATE, {})
    today = dt.date.today().isoformat()

    newly_added = []
    for it in enriched:
        url = it["url"]
        if url in articles:
            continue  # already known — the brain doesn't relearn it
        rec = {
            "id": _article_id(url),
            "url": url,
            "title": it["title"],
            "source": it["source"],
            "published": it.get("published"),
            "date_added": today,
            "plain_summary": it.get("plain_summary", ""),
            "keywords": it.get("keywords", []),
            "relevance": it.get("relevance", ""),
            "highlight": it.get("relevance") == "high",
        }
        articles[url] = rec
        by_date.setdefault(today, []).append(rec["id"])
        for topic in rec["keywords"]:
            by_topic.setdefault(topic, []).append(rec["id"])
        newly_added.append(rec)

    _save(ARTICLES, articles)
    _save(BY_TOPIC, by_topic)
    _save(BY_DATE, by_date)
    return newly_added


def all_records() -> dict:
    return _load(ARTICLES, {})


def topic_index() -> dict:
    return _load(BY_TOPIC, {})


def date_index() -> dict:
    return _load(BY_DATE, {})
