"""One-time (and safe-to-repeat) reprocessing: assign cluster_ids to every stored
article so the website can group same-story duplicates.

WHAT IT DOES
  Loads all articles from the brain, asks Claude to group same-story ones, and
  writes a shared cluster_id onto each. The website then renders one card per
  cluster with all the source links.

COST
  Uses LLM calls (grouping is done in batches). This is a ONE-TIME cleanup for
  the backlog of existing articles. Going forward, main.py assigns cluster_ids
  to new articles automatically, so you won't need to run this again unless you
  want to re-cluster everything from scratch.

SAFE TO RE-RUN
  It only groups articles; it never deletes anything. Re-running re-groups.

HOW TO RUN
  Locally:   python recluster.py
  Or:        trigger the "Recluster (run once)" workflow from the Actions tab.

BATCHING
  Clustering compares titles within a batch. Very large corpora are processed in
  chunks of BATCH so a single prompt doesn't get unwieldy; duplicates that span
  chunk boundaries are rare for a niche weekly feed but possible — re-running or
  a larger BATCH catches them. Default BATCH=40.
"""
from __future__ import annotations
import os
import hashlib
from src import brain
from src.cluster import group_indices

BATCH = 40


def _cluster_id(urls: list[str]) -> str:
    """Deterministic id from the member URLs so re-runs are stable."""
    joined = "|".join(sorted(urls))
    return "c_" + hashlib.sha1(joined.encode("utf-8")).hexdigest()[:10]


def main() -> None:
    articles = brain.all_records()          # {url: rec}
    records = list(articles.values())
    if not records:
        print("No articles in the brain yet — nothing to cluster.")
        return

    print(f"clustering {len(records)} stored articles in batches of {BATCH}...")
    url_to_cluster: dict[str, str] = {}
    total_clusters = 0

    for start in range(0, len(records), BATCH):
        chunk = records[start:start + BATCH]
        groups = group_indices(chunk)
        for g in groups:
            member_urls = [chunk[i]["url"] for i in g]
            cid = _cluster_id(member_urls)
            for u in member_urls:
                url_to_cluster[u] = cid
            total_clusters += 1
        print(f"  batch {start//BATCH + 1}: {len(chunk)} articles -> "
              f"{len(groups)} groups")

    brain.set_cluster_ids(url_to_cluster)
    merged = len(records) - total_clusters
    print(f"done. {len(records)} articles -> {total_clusters} clusters "
          f"({merged} duplicate(s) merged).")
    print("Rebuild the site (next scheduled run, or run main.py) to see the "
          "grouped cards.")


if __name__ == "__main__":
    main()
