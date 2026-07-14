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

    # Group same-story articles and persist a shared cluster_id on each, so the
    # WEBSITE can merge duplicates (it reads cluster_id, no LLM at build time).
    from src.cluster import group_indices, cluster_articles
    import hashlib
    if new_records:
        groups = group_indices(new_records)
        url_to_cluster = {}
        for g in groups:
            member_urls = [new_records[i]["url"] for i in g]
            cid = "c_" + hashlib.sha1("|".join(sorted(member_urls)).encode()).hexdigest()[:10]
            for u in member_urls:
                url_to_cluster[u] = cid
        brain.set_cluster_ids(url_to_cluster)
        print(f"assigned cluster ids to {len(new_records)} new articles")

    build_site()
    print("website rebuilt from the full brain")

    # Build the email from clusters (one blurb per story, all outlet links).
    clusters = cluster_articles(new_records)
    print(f"{len(clusters)} clusters (stories) after grouping duplicates")

    import datetime as _dt
    week_start = (_dt.date.today() - _dt.timedelta(days=7)).isoformat()
    week_end = _dt.date.today().isoformat()
    period = f"{week_start} to {week_end}"
    email_html = build_email_html(clusters, site_url=SITE_URL, period_label=period)
    if os.environ.get("SMTP_HOST"):
        send_email(email_html)
        print("email sent")
    else:
        print("SMTP_HOST not set — skipping email (local run)")


if __name__ == "__main__":
    main()
