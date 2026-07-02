# Superhot Rock Geothermal — Daily Digest + Knowledge Base

Runs itself once a day on **GitHub Actions** Each morning it:

1. **Collects** geothermal news (RSS feeds + Google News searches).
2. **Filters** to superhot-rock-relevant items.
3. **Skips** anything already in the knowledge base (no wasted AI cost).
4. **Summarizes + tags** each new item with Claude, in plain language.
5. **Adds** them to the "brain" — accumulating files in this repo.
6. **Rebuilds the website** — categorized by date, by topic, with highlights.
7. **Emails** you the day's new items via SMTP.

## The brain (knowledge/)

- `articles.json` — every article ever kept, keyed by URL (never stored twice).
- `by_topic.json` — topic -> article IDs (drives the topic pages).
- `by_date.json` — date -> article IDs (drives the date pages).

## The website (docs/, served by GitHub Pages)

- `index.html` — highlights + the latest day.
- `dates/` — browse by date.
- `topics/` — browse by topic (drilling, well construction, materials,
  electronics, sensors, subsurface mapping).
