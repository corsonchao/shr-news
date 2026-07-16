"""Rebuild ONLY the website from the existing knowledge base.

Use this whenever you change the website's look/layout (website.py) or after
running recluster.py, and want to regenerate the site WITHOUT:
  - scraping any news
  - making any LLM calls
  - sending any email
  - changing the knowledge base

It just reads knowledge/*.json and rewrites docs/. Safe, fast, free, no API key
needed.

HOW TO RUN
  Locally:   python rebuild_site.py
  Or:        trigger the "Rebuild website only" workflow from the Actions tab.
"""
from __future__ import annotations
from src.website import build_site


def main() -> None:
    build_site()
    print("website rebuilt from the existing knowledge base "
          "(no scraping, no email, no LLM calls).")


if __name__ == "__main__":
    main()
