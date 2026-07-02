"""Collect candidate articles from RSS feeds and Google News RSS queries."""
from __future__ import annotations
import urllib.parse
import datetime as dt
import feedparser  # https://feedparser.readthedocs.io/ [verified standard RSS/Atom lib]


def _google_news_rss_url(query: str) -> str:
    # NOTE: format widely used but not officially documented by Google.
    # check_feeds.py confirms it returns items.
    q = urllib.parse.quote(query)
    return f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"


def _parse_entry(entry, source_name: str) -> dict:
    published = None
    if getattr(entry, "published_parsed", None):
        published = dt.datetime(*entry.published_parsed[:6], tzinfo=dt.timezone.utc)
    return {
        "source": source_name,
        "title": getattr(entry, "title", "").strip(),
        "url": getattr(entry, "link", "").strip(),
        "snippet": getattr(entry, "summary", "").strip(),
        "published": published.isoformat() if published else None,
    }


def collect(config: dict, since_hours: int = 36) -> list[dict]:
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=since_hours)
    items: list[dict] = []

    for feed in config.get("rss_feeds", []):
        parsed = feedparser.parse(feed["url"])
        for e in parsed.entries:
            items.append(_parse_entry(e, feed["name"]))

    for gn in config.get("google_news", []):
        parsed = feedparser.parse(_google_news_rss_url(gn["query"]))
        for e in parsed.entries:
            items.append(_parse_entry(e, f"GoogleNews:{gn['name']}"))

    def _recent(it: dict) -> bool:
        if not it["published"]:
            return True
        return dt.datetime.fromisoformat(it["published"]) >= cutoff

    items = [it for it in items if it["url"] and _recent(it)]

    seen, deduped = set(), []
    for it in items:
        if it["url"] in seen:
            continue
        seen.add(it["url"])
        deduped.append(it)
    return deduped
