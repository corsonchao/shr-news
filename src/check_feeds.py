"""Verify which feed URLs in feeds.yaml return items. Run: python -m src.check_feeds"""
from __future__ import annotations
import urllib.parse
import feedparser
import yaml


def main() -> None:
    with open("feeds.yaml", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    print("=== RSS feeds ===")
    for feed in cfg.get("rss_feeds", []):
        n = len(feedparser.parse(feed["url"]).entries)
        print(f"[{'OK ' if n else 'EMPTY/FAIL'}] {n:>3}  {feed['name']}  <{feed['url']}>")

    print("\n=== Google News queries ===")
    for gn in cfg.get("google_news", []):
        q = urllib.parse.quote(gn["query"])
        url = f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"
        n = len(feedparser.parse(url).entries)
        print(f"[{'OK ' if n else 'EMPTY/FAIL'}] {n:>3}  {gn['name']}")


if __name__ == "__main__":
    main()
