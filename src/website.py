"""Build the static website from the brain.

Generates, under docs/ (served free by GitHub Pages):
    docs/index.html            -> home: latest highlights + recent days
    docs/dates/INDEX.html      -> browse by date
    docs/dates/<YYYY-MM-DD>.html
    docs/topics/INDEX.html     -> browse by topic
    docs/topics/<topic>.html
Everything is read from the brain (knowledge/*.json), so the site always
reflects the full accumulated corpus, not just today.
"""
from __future__ import annotations
import html
import os
import datetime as dt
from src import brain

DOCS = "docs"
_TAG_COLORS = {
    "drilling": "#b45309", "well construction": "#0369a1", "materials": "#7c3aed",
    "electronics": "#be123c", "sensors": "#047857", "subsurface mapping": "#1d4ed8",
}


def _slug(s: str) -> str:
    return s.lower().replace(" ", "-")


def _tag(kw: str, prefix: str = "") -> str:
    color = _TAG_COLORS.get(kw, "#475569")
    href = f"{prefix}topics/{_slug(kw)}.html"
    return (f'<a href="{href}" style="background:{color};color:#fff;'
            f'border-radius:10px;padding:2px 9px;font-size:12px;margin:0 4px 4px 0;'
            f'display:inline-block;text-decoration:none;">{html.escape(kw)}</a>')


def _page(title: str, inner: str, prefix: str = "") -> str:
    return f"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title></head>
<body style="font-family:system-ui,sans-serif;max-width:760px;margin:0 auto;
      padding:24px;color:#0f172a;background:#fff;">
  <nav style="margin-bottom:20px;font-size:14px;">
    <a href="{prefix}index.html" style="margin-right:14px;">Home</a>
    <a href="{prefix}dates/INDEX.html" style="margin-right:14px;">By date</a>
    <a href="{prefix}topics/INDEX.html">By topic</a>
  </nav>
  <h1 style="margin-bottom:16px;">{html.escape(title)}</h1>
  {inner}
  <footer style="margin-top:36px;color:#94a3b8;font-size:12px;border-top:
    1px solid #e2e8f0;padding-top:12px;">
    Summaries generated automatically; links go to original sources.
  </footer>
</body></html>"""


def _card(rec: dict, prefix: str = "") -> str:
    tags = "".join(_tag(k, prefix) for k in rec.get("keywords", []))
    star = " ⭐" if rec.get("highlight") else ""
    return f"""
    <article style="border-bottom:1px solid #e2e8f0;padding:16px 0;">
      <a href="{html.escape(rec['url'], quote=True)}" style="font-size:17px;
         font-weight:600;color:#0f172a;text-decoration:none;">
         {html.escape(rec['title'])}{star}</a>
      <div style="color:#64748b;font-size:13px;margin:3px 0 8px;">
         {html.escape(rec['source'])} &middot; added {rec['date_added']}
         &middot; relevance: {html.escape(rec.get('relevance',''))}</div>
      <p style="margin:0 0 10px;color:#334155;line-height:1.5;">
         {html.escape(rec.get('plain_summary',''))}</p>
      <div>{tags}</div>
    </article>"""


def _write(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def build_site() -> None:
    articles = brain.all_records()                 # {url: rec}
    by_id = {r["id"]: r for r in articles.values()}
    topics = brain.topic_index()                    # {topic: [ids]}
    dates = brain.date_index()                      # {date: [ids]}

    # ---- Home: highlights + most recent day ----
    highlights = [r for r in articles.values() if r.get("highlight")]
    highlights.sort(key=lambda r: r["date_added"], reverse=True)
    recent_days = sorted(dates.keys(), reverse=True)[:1]
    recent_cards = ""
    for d in recent_days:
        recent_cards += f'<h2 style="font-size:16px;color:#475569;">{d}</h2>'
        recent_cards += "".join(_card(by_id[i]) for i in dates[d] if i in by_id)
    home_inner = "<h2 style='font-size:16px;color:#475569;'>Highlights</h2>"
    home_inner += ("".join(_card(r) for r in highlights[:8])
                   or "<p>No highlights yet.</p>")
    home_inner += "<hr style='margin:24px 0;border:none;border-top:1px solid #e2e8f0;'>"
    home_inner += "<h2 style='font-size:18px;'>Latest day</h2>" + (recent_cards or "<p>Nothing yet.</p>")
    _write(os.path.join(DOCS, "index.html"),
           _page("Superhot Rock Geothermal — Knowledge Base", home_inner))

    # ---- By date ----
    date_links = "".join(
        f'<li><a href="{d}.html">{d}</a> ({len(ids)} items)</li>'
        for d, ids in sorted(dates.items(), reverse=True))
    _write(os.path.join(DOCS, "dates", "INDEX.html"),
           _page("Browse by date", f"<ul>{date_links}</ul>", prefix="../"))
    for d, ids in dates.items():
        cards = "".join(_card(by_id[i], prefix="../") for i in ids if i in by_id)
        _write(os.path.join(DOCS, "dates", f"{d}.html"),
               _page(f"News for {d}", cards, prefix="../"))

    # ---- By topic ----
    topic_links = "".join(
        f'<li><a href="{_slug(t)}.html">{html.escape(t)}</a> ({len(ids)} items)</li>'
        for t, ids in sorted(topics.items()))
    _write(os.path.join(DOCS, "topics", "INDEX.html"),
           _page("Browse by topic", f"<ul>{topic_links}</ul>", prefix="../"))
    for t, ids in topics.items():
        # newest first, de-duped
        seen, ordered = set(), []
        for i in sorted(ids, key=lambda x: by_id.get(x, {}).get("date_added", ""),
                        reverse=True):
            if i in by_id and i not in seen:
                seen.add(i)
                ordered.append(i)
        cards = "".join(_card(by_id[i], prefix="../") for i in ordered)
        _write(os.path.join(DOCS, "topics", f"{_slug(t)}.html"),
               _page(f"Topic: {t}", cards, prefix="../"))
