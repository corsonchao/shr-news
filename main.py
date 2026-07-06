"""Daily pipeline: collect -> filter -> skip-known -> summarize -> brain -> site -> email."""
from __future__ import annotations
import os
import yaml

from src.collect import collect
from src.filter import filter_relevant
from src import brain
from src.summarize import summarize_all
from src.website import build_site
from src.deliver import build_email_html, send_email

SITE_URL = os.environ.get("SITE_URL", "")  # e.g. https://you.github.io/shr-digest/


def main() -> None:
    with open("feeds.yaml", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    topics = cfg["topics"]

    # Weekly run: collect the past 7 days (168h). A little overlap with the
    # previous week is fine — the brain de-dupes by URL, so nothing repeats.
    items = collect(cfg, since_hours=168)
    print(f"collected {len(items)}")

    items = filter_relevant(items, cfg["relevance"])
    print(f"{len(items)} passed relevance gate")

    # Skip anything the brain already knows -> no wasted LLM tokens on old news.
    known = brain.load_known_urls()
    items = [it for it in items if it["url"] not in known]
    print(f"{len(items)} are new (not already in the brain)")

    enriched = summarize_all(items, topics, drop_low=True)
    print(f"{len(enriched)} summarized and kept")

    new_records = brain.add_articles(enriched)
    print(f"{len(new_records)} added to the brain")

    build_site()
    print("website rebuilt from the full brain")

    import datetime as _dt
    week_start = (_dt.date.today() - _dt.timedelta(days=7)).isoformat()
    week_end = _dt.date.today().isoformat()
    period = f"{week_start} to {week_end}"
    email_html = build_email_html(new_records, site_url=SITE_URL, period_label=period)
    if os.environ.get("SMTP_HOST"):
        send_email(email_html)
        print("email sent")
    else:
        print("SMTP_HOST not set — skipping email (local run)")


if __name__ == "__main__":
    main()
