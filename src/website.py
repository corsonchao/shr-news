"""Build the static website from the brain.

Generates, under docs/ (served free by GitHub Pages):
    docs/style.css             -> shared stylesheet (one file, all pages)
    docs/index.html            -> home: hero + highlights + latest additions
    docs/dates/INDEX.html      -> browse by date
    docs/dates/<YYYY-MM-DD>.html
    docs/topics/INDEX.html     -> browse by topic
    docs/topics/<topic>.html
Everything is read from the brain (knowledge/*.json), so the site always
reflects the full accumulated corpus, not just today.

DESIGN
  Palette derives from the subject: rock heated to the superhot-geothermal range
  glows from deep basalt through molten amber. Dark "deep earth" background,
  incandescent accents used with restraint, monospace for data (dates, counts,
  temperatures-of-the-domain vernacular). Fully responsive; respects reduced
  motion; light/dark handled by a single dark-first theme with warm neutrals.
"""
from __future__ import annotations
import html
import os
import datetime as dt
from src import brain

DOCS = "docs"

# Thermal palette mapped to the six domains. Colors sit on the same
# basalt->amber heat ramp so the tags read as a coherent system, not confetti.
_TAG_COLORS = {
    "drilling":          "#e8623a",  # molten orange
    "well construction": "#f2933c",  # amber
    "materials":         "#d94f6a",  # hot magenta-red
    "electronics":       "#c77dff",  # plasma violet
    "sensors":           "#4bb8a9",  # cooled teal (instrument)
    "subsurface mapping":"#5a9bd8",  # cool blue (depth)
    "legislation":       "#9aa5b1",  # slate grey (policy context)
    "funding":           "#6bbf59",  # green (money)
}


def _slug(s: str) -> str:
    return s.lower().replace(" ", "-")


def _tag(kw: str, prefix: str = "") -> str:
    color = _TAG_COLORS.get(kw, "#8a8f98")
    href = f"{prefix}topics/{_slug(kw)}.html"
    return (f'<a class="tag" href="{href}" '
            f'style="--tag:{color}">{html.escape(kw)}</a>')


STYLE = """
:root{
  --bg:#0e0b09; --bg2:#171310; --panel:#1c1714; --panel2:#231d18;
  --line:#332a22; --ink:#f3ece3; --ink2:#c9bcac; --ink3:#8f8172;
  --amber:#f2933c; --molten:#e8623a; --ember:#d94f6a;
  --glow:0 0 0 1px rgba(242,147,60,.15), 0 8px 30px -12px rgba(232,98,58,.35);
  --radius:14px;
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{
  margin:0; background:
    radial-gradient(1200px 600px at 70% -10%, rgba(232,98,58,.12), transparent 60%),
    radial-gradient(900px 500px at 10% 0%, rgba(242,147,60,.08), transparent 55%),
    var(--bg);
  color:var(--ink);
  font-family:"Inter","Segoe UI",system-ui,-apple-system,sans-serif;
  line-height:1.55; -webkit-font-smoothing:antialiased;
}
a{color:inherit}
.wrap{max-width:960px; margin:0 auto; padding:0 22px}

/* top nav */
.nav{position:sticky; top:0; z-index:20; backdrop-filter:blur(10px);
  background:rgba(14,11,9,.72); border-bottom:1px solid var(--line)}
.nav .wrap{display:flex; align-items:center; gap:26px; height:60px}
.brand{display:flex; align-items:center; gap:10px; font-weight:700;
  letter-spacing:.3px; text-decoration:none}
.brand .dot{width:11px; height:11px; border-radius:50%;
  background:radial-gradient(circle at 30% 30%, #ffd9a0, var(--molten) 60%, #7a1f10);
  box-shadow:0 0 12px 2px rgba(232,98,58,.6)}
.nav a.link{color:var(--ink2); text-decoration:none; font-size:14px;
  font-weight:500; padding:6px 0; border-bottom:2px solid transparent}
.nav a.link:hover{color:var(--ink); border-bottom-color:var(--amber)}
.nav .spacer{flex:1}

/* hero */
.hero{position:relative; padding:72px 0 40px; overflow:hidden}
.hero .eyebrow{font-family:"JetBrains Mono",ui-monospace,monospace;
  font-size:12px; letter-spacing:2.5px; text-transform:uppercase;
  color:var(--amber); margin:0 0 14px}
.hero h1{font-size:clamp(30px,5vw,52px); line-height:1.05; margin:0 0 16px;
  font-weight:800; letter-spacing:-.5px;
  background:linear-gradient(180deg,#fff2e2,#f2933c 120%);
  -webkit-background-clip:text; background-clip:text; color:transparent}
.hero p.lede{max-width:620px; color:var(--ink2); font-size:18px; margin:0 0 26px}
.hero .depthbar{display:flex; gap:14px; flex-wrap:wrap;
  font-family:"JetBrains Mono",ui-monospace,monospace; font-size:12.5px;
  color:var(--ink3)}
.hero .depthbar b{color:var(--ink); font-weight:600}
.thermline{position:absolute; right:-40px; top:0; bottom:0; width:220px;
  background:linear-gradient(180deg,transparent, rgba(242,147,60,.18) 40%,
    rgba(232,98,58,.32) 70%, rgba(122,31,16,.5)); filter:blur(30px);
  pointer-events:none}

/* section headers */
.sec{padding:14px 0 8px; margin-top:22px;
  display:flex; align-items:baseline; gap:12px}
.sec h2{font-size:15px; letter-spacing:1.5px; text-transform:uppercase;
  color:var(--ink2); font-weight:700; margin:0}
.sec .rule{flex:1; height:1px; background:linear-gradient(90deg,var(--line),transparent)}
.sec .count{font-family:"JetBrains Mono",monospace; font-size:12px; color:var(--ink3)}

/* card grid */
.grid{display:grid; grid-template-columns:repeat(auto-fill,minmax(280px,1fr));
  gap:16px; padding:8px 0 4px}
.card{background:linear-gradient(180deg,var(--panel2),var(--panel));
  border:1px solid var(--line); border-radius:var(--radius); padding:18px 18px 16px;
  display:flex; flex-direction:column; gap:10px; transition:transform .15s ease,
  box-shadow .15s ease, border-color .15s ease}
.card:hover{transform:translateY(-3px); box-shadow:var(--glow);
  border-color:rgba(242,147,60,.4)}
.card.hl{border-color:rgba(242,147,60,.45);
  background:linear-gradient(180deg,#241a12,var(--panel))}
.card .meta{font-family:"JetBrains Mono",monospace; font-size:11.5px;
  color:var(--ink3); display:flex; align-items:center; gap:8px; flex-wrap:wrap}
.card .src{color:var(--amber)}
.card .rel{margin-left:auto; padding:2px 7px; border-radius:20px;
  border:1px solid var(--line); text-transform:uppercase; letter-spacing:.5px}
.card .rel.high{color:var(--molten); border-color:rgba(232,98,58,.5)}
.card h3{margin:0; font-size:17px; line-height:1.3; font-weight:650}
.card h3 a{text-decoration:none}
.card h3 a:hover{color:var(--amber)}
.card .flame{color:var(--amber)}
.card p{margin:0; color:var(--ink2); font-size:14.5px; flex:1}
.tags{display:flex; flex-wrap:wrap; gap:7px; margin-top:2px}
.tag{--tag:#8a8f98; text-decoration:none; font-size:12px; font-weight:600;
  padding:3px 10px; border-radius:20px; color:var(--tag);
  border:1px solid color-mix(in srgb, var(--tag) 40%, transparent);
  background:color-mix(in srgb, var(--tag) 12%, transparent); white-space:nowrap}
.tag:hover{background:color-mix(in srgb, var(--tag) 22%, transparent)}
.figures{margin:4px 0 2px; padding:9px 12px; border-radius:8px;
  background:rgba(242,147,60,.08); border-left:3px solid var(--amber)}
.figures .figlabel{display:block; font-family:"JetBrains Mono",monospace;
  font-size:10.5px; letter-spacing:1px; text-transform:uppercase;
  color:var(--amber); margin-bottom:4px}
.figures ul{margin:0; padding-left:16px; color:var(--ink2); font-size:13.5px}
.figures li{margin:0 0 2px}
.srclinks{margin-top:8px; font-size:12.5px; color:var(--ink3);
  display:flex; flex-wrap:wrap; gap:2px 4px}
.srclinks a{color:var(--amber); text-decoration:none}
.srclinks a:hover{text-decoration:underline}

/* index list pages (dates / topics) */
.tiles{display:grid; grid-template-columns:repeat(auto-fill,minmax(220px,1fr));
  gap:14px; padding:14px 0}
.tile{background:linear-gradient(180deg,var(--panel2),var(--panel));
  border:1px solid var(--line); border-radius:var(--radius); padding:18px 18px;
  text-decoration:none; display:flex; flex-direction:column; gap:6px;
  transition:transform .15s, border-color .15s, box-shadow .15s}
.tile:hover{transform:translateY(-3px); border-color:rgba(242,147,60,.4);
  box-shadow:var(--glow)}
.tile .k{font-size:18px; font-weight:700}
.tile .n{font-family:"JetBrains Mono",monospace; font-size:12px; color:var(--ink3)}
.tile .swatch{width:26px; height:5px; border-radius:3px; margin-bottom:2px}

.empty{color:var(--ink3); font-size:15px; padding:24px 0}

footer{margin-top:56px; border-top:1px solid var(--line); padding:26px 0 50px;
  color:var(--ink3); font-size:12.5px}
footer a{color:var(--ink2)}

@media (max-width:520px){ .hero{padding:48px 0 30px} .nav .wrap{gap:16px} }
@media (prefers-reduced-motion:reduce){ *{transition:none!important; scroll-behavior:auto} }
"""


def _head(title: str, prefix: str) -> str:
    return f"""<!doctype html><html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{prefix}style.css">
</head><body>"""


def _nav(prefix: str) -> str:
    return f"""
<nav class="nav"><div class="wrap">
  <a class="brand" href="{prefix}index.html"><span class="dot"></span>Superhot&nbsp;Rock&nbsp;Watch</a>
  <span class="spacer"></span>
  <a class="link" href="{prefix}index.html">Latest</a>
  <a class="link" href="{prefix}topics/INDEX.html">Topics</a>
  <a class="link" href="{prefix}dates/INDEX.html">Archive</a>
</div></nav>"""


def _foot() -> str:
    return ("""<footer><div class="wrap">
  Plain-language summaries generated automatically from public sources.
  Every card links to its original article. Superhot Rock Watch is an
  independent news tracker and is not affiliated with the sources it cites.
</div></footer></body></html>""")


def _card(rec: dict, prefix: str = "") -> str:
    tags = "".join(_tag(k, prefix) for k in rec.get("keywords", []))
    hl = rec.get("highlight")
    flame = '<span class="flame">&#9650;</span> ' if hl else ""
    rel = html.escape(rec.get("relevance", ""))
    rel_cls = "rel high" if rel == "high" else "rel"
    return f"""
    <article class="card{' hl' if hl else ''}">
      <div class="meta">
        <span class="src">{html.escape(rec['source'])}</span>
        <span>&middot; {rec['date_added']}</span>
        <span class="{rel_cls}">{rel}</span>
      </div>
      <h3><a href="{html.escape(rec['url'], quote=True)}" target="_blank"
             rel="noopener">{flame}{html.escape(rec['title'])}</a></h3>
      <p>{html.escape(rec.get('plain_summary',''))}</p>
      <div class="tags">{tags}</div>
    </article>"""


def _cluster_card(members: list[dict], prefix: str = "") -> str:
    """Render one card for a group of same-story articles: merged tags, key
    figures, and every outlet as a labeled link. Falls back to a plain single
    card when the group has one member."""
    if len(members) == 1:
        return _card(members[0], prefix)

    # Merge display fields from the members (no LLM at build time — we use the
    # richest stored summary and union the tags/figures).
    best = max(members, key=lambda m: len(m.get("plain_summary", "")))
    hl = any(m.get("highlight") for m in members)
    rels = [m.get("relevance", "") for m in members]
    rel = "high" if "high" in rels else ("medium" if "medium" in rels else "low")
    rel_cls = "rel high" if rel == "high" else "rel"
    flame = '<span class="flame">&#9650;</span> ' if hl else ""

    seen_kw, kws = set(), []
    for m in members:
        for k in m.get("keywords", []):
            if k not in seen_kw:
                seen_kw.add(k); kws.append(k)
    tags = "".join(_tag(k, prefix) for k in kws)

    from src.cluster import _merge_figures
    figs = _merge_figures(members)
    figs_html = ""
    if figs:
        lis = "".join(f"<li>{html.escape(f)}</li>" for f in figs)
        figs_html = (f'<div class="figures"><span class="figlabel">Key figures</span>'
                     f'<ul>{lis}</ul></div>')

    # every outlet as a labeled link
    src_links = " &middot; ".join(
        f'<a href="{html.escape(m["url"], quote=True)}" target="_blank" '
        f'rel="noopener">{html.escape(m["source"])}</a>' for m in members)

    date_added = min(m.get("date_added", "") for m in members)
    return f"""
    <article class="card{' hl' if hl else ''}">
      <div class="meta">
        <span class="src">{len(members)} sources</span>
        <span>&middot; {date_added}</span>
        <span class="{rel_cls}">{rel}</span>
      </div>
      <h3>{flame}{html.escape(best['title'])}</h3>
      <p>{html.escape(best.get('plain_summary',''))}</p>
      {figs_html}
      <div class="tags">{tags}</div>
      <div class="srclinks">{src_links}</div>
    </article>"""


def _group_by_cluster(recs: list[dict]) -> list[list[dict]]:
    """Group a list of article records by cluster_id. Records without a
    cluster_id are treated as their own singleton group. Preserves order by
    first appearance; sorts groups by newest date_added within the caller."""
    groups: dict[str, list[dict]] = {}
    singletons: list[list[dict]] = []
    for r in recs:
        cid = r.get("cluster_id")
        if not cid:
            singletons.append([r])
        else:
            groups.setdefault(cid, []).append(r)
    return list(groups.values()) + singletons


def _grid(cards: str, empty_msg: str) -> str:
    return f'<div class="grid">{cards}</div>' if cards else f'<div class="empty">{empty_msg}</div>'


def _sec(title: str, count_text: str = "") -> str:
    c = f'<span class="count">{count_text}</span>' if count_text else ""
    return f'<div class="sec"><h2>{html.escape(title)}</h2><span class="rule"></span>{c}</div>'


def _write(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def build_site() -> None:
    articles = brain.all_records()
    by_id = {r["id"]: r for r in articles.values()}
    topics = brain.topic_index()
    dates = brain.date_index()
    total = len(articles)

    # shared stylesheet
    _write(os.path.join(DOCS, "style.css"), STYLE)

    # ---------- HOME ----------
    highlights = [r for r in articles.values() if r.get("highlight")]
    highlights.sort(key=lambda r: r["date_added"], reverse=True)
    latest_days = sorted(dates.keys(), reverse=True)[:1]

    hero = f"""
<header class="hero"><div class="thermline"></div><div class="wrap">
  <p class="eyebrow">Deep geothermal &middot; drilling to sensing</p>
  <h1>Super Hot News</h1>
  <p class="lede">A daily, plain-language tracker of superhot rock geothermal
     progress &mdash; the drilling, materials, electronics, sensing and
     subsurface work moving it from lab to field.</p>
  <div class="depthbar">
    <span><b>{total}</b> articles tracked</span>
    <span><b>{len(topics)}</b> topics</span>
    <span><b>{len(dates)}</b> days logged</span>
  </div>
</div></header>"""

    # Highlights and latest — grouped into clusters so duplicates merge.
    hl_groups = _group_by_cluster(highlights[:12])
    hl_cards = "".join(_cluster_card(g) for g in hl_groups[:6])
    latest_cards = ""
    for d in latest_days:
        day_recs = [by_id[i] for i in dates[d] if i in by_id]
        latest_groups = _group_by_cluster(day_recs)
        latest_cards += "".join(_cluster_card(g) for g in latest_groups)

    body = (_head("Superhot Rock Watch", "") + _nav("") + hero + '<div class="wrap">'
            + _sec("Highlights", f"{len(highlights)} flagged")
            + _grid(hl_cards, "No highlights yet — check back after the next run.")
            + _sec("Latest additions", latest_days[0] if latest_days else "")
            + _grid(latest_cards, "Nothing logged yet. The tracker fills on its next scheduled run.")
            + "</div>" + _foot())
    _write(os.path.join(DOCS, "index.html"), body)

    # ---------- BY DATE ----------
    date_tiles = "".join(
        f'<a class="tile" href="{d}.html"><span class="k">{d}</span>'
        f'<span class="n">{len(set(ids))} article(s)</span></a>'
        for d in sorted(dates.keys(), reverse=True) for ids in [dates[d]])
    di = (_head("Archive by date", "../") + _nav("../") + '<div class="wrap">'
          + _sec("Archive", f"{len(dates)} day(s)")
          + (f'<div class="tiles">{date_tiles}</div>' if date_tiles
             else '<div class="empty">No entries yet.</div>')
          + "</div>" + _foot())
    _write(os.path.join(DOCS, "dates", "INDEX.html"), di)
    for d, ids in dates.items():
        day_recs = [by_id[i] for i in ids if i in by_id]
        groups = _group_by_cluster(day_recs)
        cards = "".join(_cluster_card(g, "../") for g in groups)
        page = (_head(f"News for {d}", "../") + _nav("../") + '<div class="wrap">'
                + _sec(f"Added {d}") + _grid(cards, "No entries for this day.")
                + "</div>" + _foot())
        _write(os.path.join(DOCS, "dates", f"{d}.html"), page)

    # ---------- BY TOPIC ----------
    topic_tiles = ""
    for t in sorted(topics.keys()):
        color = _TAG_COLORS.get(t, "#8a8f98")
        n = len(set(topics[t]))
        topic_tiles += (f'<a class="tile" href="{_slug(t)}.html">'
                        f'<span class="swatch" style="background:{color}"></span>'
                        f'<span class="k">{html.escape(t)}</span>'
                        f'<span class="n">{n} article(s)</span></a>')
    ti = (_head("Topics", "../") + _nav("../") + '<div class="wrap">'
          + _sec("Topics", f"{len(topics)} area(s)")
          + (f'<div class="tiles">{topic_tiles}</div>' if topic_tiles
             else '<div class="empty">No topics yet.</div>')
          + "</div>" + _foot())
    _write(os.path.join(DOCS, "topics", "INDEX.html"), ti)
    for t, ids in topics.items():
        seen, ordered = set(), []
        for i in sorted(ids, key=lambda x: by_id.get(x, {}).get("date_added", ""),
                        reverse=True):
            if i in by_id and i not in seen:
                seen.add(i); ordered.append(i)
        topic_recs = [by_id[i] for i in ordered]
        groups = _group_by_cluster(topic_recs)
        cards = "".join(_cluster_card(g, "../") for g in groups)
        page = (_head(f"Topic: {t}", "../") + _nav("../") + '<div class="wrap">'
                + _sec(t, f"{len(ordered)} article(s)")
                + _grid(cards, "No articles tagged with this topic yet.")
                + "</div>" + _foot())
        _write(os.path.join(DOCS, "topics", f"{_slug(t)}.html"), page)
