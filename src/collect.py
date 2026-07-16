"""Collect candidate articles from RSS feeds and Google News RSS queries."""
from __future__ import annotations
import urllib.parse
import datetime as dt
import feedparser


def _google_news_rss_url(query: str) -> str:
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


def _google_news_publisher(entry) -> str | None:
    """Google News RSS entries carry the real publisher in two places:
      1. a <source> element -> feedparser exposes entry.source.title
      2. the title ends with '  - Publisher Name'
    We prefer (1); fall back to (2). Returns None if neither is present."""
    src = getattr(entry, "source", None)
    if src is not None:
        title = getattr(src, "title", None) or (src.get("title") if isinstance(src, dict) else None)
        if title and title.strip():
            return title.strip()
    # Fall back to the title suffix after the last ' - '
    title = getattr(entry, "title", "") or ""
    if " - " in title:
        candidate = title.rsplit(" - ", 1)[-1].strip()
        if candidate and len(candidate) < 60:
            return candidate
    return None


def _clean_google_title(title: str, publisher: str | None) -> str:
    """Strip the ' - Publisher' suffix Google News appends to titles."""
    if publisher and title.endswith(f" - {publisher}"):
        return title[: -(len(publisher) + 3)].strip()
    return title


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
            publisher = _google_news_publisher(e)
            source_label = publisher if publisher else f"News: {gn['name']}"
            item = _parse_entry(e, source_label)
            item["title"] = _clean_google_title(item["title"], publisher)
            item["from_broad_search"] = True   # flag for the relevance filter
            items.append(item)

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
