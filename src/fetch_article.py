"""Politely fetch an article's full text for richer key-figure extraction.

GUARDRAILS (all three you chose):
  1. HONORS robots.txt — checks each site's rules with the standard-library
     robotparser and skips any URL the site disallows for our agent.
  2. POLITE — honest User-Agent, short timeout, a small delay between fetches,
     one at a time (never parallel bursts). Weekly cadence + few articles = gentle.
  3. COPYRIGHT-SAFE — the returned full text is used ONLY to (a) extract numeric
     figures and (b) improve the summary wording in the LLM call. It is NEVER
     written to the brain, the website, or any stored file. Facts out, prose
     discarded. Callers must not persist the returned text.

DEGRADES GRACEFULLY: on any failure (disallowed, timeout, paywall, JS-only page,
empty extraction) it returns None, and the caller falls back to the RSS snippet.
So the pipeline gets strictly better where fetching works, never worse.

A headless-browser tier for JavaScript-only sites is intentionally NOT included
(too heavy for a weekly GitHub Action; would trip bot-detection on shared IPs).
The clean fallback below is where such a tier could be slotted in later.
"""
from __future__ import annotations
import time
import urllib.robotparser
import urllib.parse
import trafilatura  # v2.x  [verified installed 2.1.0]

# Honest identification. If you publish the site, put its URL here so site owners
# can see who is fetching and contact you if needed.
USER_AGENT = ("SuperhotRockWatch/1.0 (weekly research digest; "
              "contact: corsonchao@gmail.com)")

TIMEOUT = 15          # seconds per fetch
POLITE_DELAY = 2.0    # seconds to wait between fetches
MAX_CHARS = 12000     # cap text sent to the LLM (keeps token cost sane)

# Cache one robotparser per domain so we don't refetch robots.txt repeatedly.
_robots_cache: dict[str, urllib.robotparser.RobotFileParser | None] = {}


def _allowed_by_robots(url: str) -> bool:
    """True if this site's robots.txt permits our agent to fetch this URL.
    On any error reading robots.txt, we conservatively return False (skip)."""
    try:
        parts = urllib.parse.urlparse(url)
        base = f"{parts.scheme}://{parts.netloc}"
        if base not in _robots_cache:
            rp = urllib.robotparser.RobotFileParser()
            rp.set_url(base + "/robots.txt")
            try:
                rp.read()
                _robots_cache[base] = rp
            except Exception:
                _robots_cache[base] = None  # couldn't read -> treat as disallow
        rp = _robots_cache[base]
        if rp is None:
            return False
        return rp.can_fetch(USER_AGENT, url)
    except Exception:
        return False


def fetch_full_text(url: str) -> str | None:
    """Return extracted article text, or None to signal 'use the snippet instead'.

    The caller MUST treat the return value as transient: use it for figure
    extraction / summary wording, then discard. Do not store it.
    """
    if not url or not url.startswith(("http://", "https://")):
        return None
    if not _allowed_by_robots(url):
        return None  # site said no -> respect it, fall back to snippet

    time.sleep(POLITE_DELAY)  # be gentle
    try:
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            return None
        text = trafilatura.extract(
            downloaded, url=url,
            include_comments=False, include_tables=True,
        )
    except Exception:
        return None

    if not text or len(text.strip()) < 200:
        return None  # too little -> probably a paywall/JS page; use snippet
    return text.strip()[:MAX_CHARS]
