"""One-time backfill: seed the brain with the past week's articles.

WHAT IT CAN AND CANNOT DO
  RSS feeds and Google News RSS are rolling windows, NOT archives. This script
  grabs everything the sources CURRENTLY expose and keeps whatever falls within
  the last 7 days. If a feed only holds the last 3 days, that's all you get for
  that source — there is no way to page further back through RSS. So the true
  yield depends entirely on how much the sources still show today. For a niche
  topic this may be a handful to a few dozen articles, not a guaranteed 7 full
  days of dense coverage.

HOW TO RUN (once)
  Locally:            python backfill.py
  Or on GitHub:       trigger the "Weekly backfill" workflow from the Actions tab
                      (see .github/workflows/backfill.yml).

SAFE TO RUN ALONGSIDE THE DAILY JOB
  The brain de-duplicates by URL, so anything the daily run already saved is
  skipped, and running this won't create duplicates. After backfill, the normal
  daily runs continue seamlessly.

DAYS is how far back to reach. 7 = one week. You can bump it, but you will only
get more if the sources actually still expose older items.
"""
from __future__ import annotations
import os
import yaml

from src.collect import collect
from src.filter import filter_relevant
from src import brain
from src.summarize import summarize_all
from src.website import build_site
from src.deliver import build_email_html, send_email

DAYS = 7
SITE_URL = os.environ.get("SITE_URL", "")


def main() -> None:
    with open("feeds.yaml", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    topics = cfg["topics"]

    since_hours = DAYS * 24
    items = collect(cfg, since_hours=since_hours)
    print(f"backfill window: last {DAYS} days ({since_hours}h)")
    print(f"collected {len(items)} candidate articles the sources still expose")

    items = filter_relevant(items, cfg["relevance"])
    print(f"{len(items)} passed the relevance gate")

    known = brain.load_known_urls()
    items = [it for it in items if it["url"] not in known]
    print(f"{len(items)} are new (not already in the brain)")

    if not items:
        print("Nothing new to backfill — the brain already has everything the "
              "sources currently expose. (This is normal if the daily job has "
              "already run, or if the feeds only hold very recent items.)")
        build_site()
        return

    enriched = summarize_all(items, topics, drop_low=True)
    print(f"{len(enriched)} summarized and kept")

    new_records = brain.add_articles(enriched)
    print(f"{len(new_records)} added to the brain")

    build_site()
    print("website rebuilt from the full brain")

    # Optional: send ONE summary email of the backfilled batch. Comment out the
    # next block if you'd rather not get a large one-off email.
    if os.environ.get("SMTP_HOST") and new_records:
        email_html = build_email_html(new_records, site_url=SITE_URL)
        send_email(email_html)
        print(f"sent a one-time backfill email with {len(new_records)} items")
    else:
        print("skipping email (no SMTP configured, or nothing new)")

    print("\nNote: article dates reflect when each was PUBLISHED where the feed "
          "provided a date; items without a feed date are stamped with today's "
          "date_added, so they'll group under today on the website's by-date view.")


if __name__ == "__main__":
    main()
