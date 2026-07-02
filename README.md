# Superhot Rock Geothermal — Daily Digest + Knowledge Base

Runs itself once a day on **GitHub Actions** (a personal account — no Claude
connectors, no corporate infrastructure). Each morning it:

1. **Collects** geothermal news (RSS feeds + Google News searches).
2. **Filters** to superhot-rock-relevant items.
3. **Skips** anything already in the knowledge base (no wasted AI cost).
4. **Summarizes + tags** each new item with Claude, in plain language.
5. **Adds** them to the "brain" — accumulating files in this repo.
6. **Rebuilds the website** — categorized by date, by topic, with highlights.
7. **Emails** you the day's new items via SMTP.

## Why this design (given your constraints)

You asked about connectors, Claude Code Routines, OneDrive, and a corporate
account. Here's why the build landed where it did:

- **No Claude connectors.** Connectors act during a live chat; they don't run on
  a schedule by themselves. Your corporate account also restricts which
  connectors are allowed (GitHub wasn't available). GitHub Actions on a
  **personal** account sidesteps all of that and runs unattended.
- **Claude Code Routines** *can* run unattended in Anthropic's cloud (verified:
  https://code.claude.com/docs/en/scheduled-tasks), and would be a fine
  alternative engine — but it's in research preview, may be gated by your
  corporate admin, and adds nothing this GitHub Actions job doesn't already do.
- **The "brain" is files in this repo,** not OneDrive. The job already
  reads/writes this repo for the website, so keeping the brain here means one
  system, no extra auth, and every day's additions are a git commit you can
  inspect or roll back. OneDrive would add Microsoft Graph OAuth setup and, since
  your OneDrive is corporate, likely the same policy wall you hit with GitHub. If
  you later want a OneDrive copy for browsing, add a step that mirrors
  `knowledge/` to OneDrive — see the note in `src/brain.py`. Keep the repo as the
  source of truth.
- **Room to grow into a semantic brain.** `knowledge/articles.json` is a flat,
  embeddable corpus. To add meaning-based search later, embed each record and
  store vectors alongside — no restructuring needed.

## The brain (knowledge/)

- `articles.json` — every article ever kept, keyed by URL (never stored twice).
- `by_topic.json` — topic -> article IDs (drives the topic pages).
- `by_date.json` — date -> article IDs (drives the date pages).

## The website (docs/, served by GitHub Pages)

- `index.html` — highlights + the latest day.
- `dates/` — browse by date.
- `topics/` — browse by topic (drilling, well construction, materials,
  electronics, sensors, subsurface mapping).

## Setup

1. **Create a PERSONAL public GitHub repo** and upload these files.
2. **Verify feeds** (optional, on your own computer):
   ```
   pip install -r requirements.txt
   python -m src.check_feeds
   ```
   Keep the `OK` sources; drop the `EMPTY/FAIL` ones in `feeds.yaml`.
3. **Add repository Secrets** (Settings -> Secrets and variables -> Actions):
   `ANTHROPIC_API_KEY`, `SMTP_HOST` (`smtp.gmail.com`), `SMTP_PORT` (`587`),
   `SMTP_USER`, `SMTP_PASS` (Gmail = an **App Password**), `MAIL_TO`,
   and `SITE_URL` (e.g. `https://YOURNAME.github.io/YOURREPO/`).
4. **Enable Pages**: Settings -> Pages -> Deploy from a branch, folder `/docs`.
5. **Test**: Actions tab -> "Daily SHR Geothermal Digest" -> Run workflow. Then
   the daily schedule takes over.

## Cost

GitHub Actions: free (public repo). Claude: a few short Haiku calls per new
article — fractions of a cent/day. Feeds: free.

## Tuning

- Schedule: the `cron` line in `.github/workflows/daily-digest.yml` (UTC; min
  interval 5 min; avoid `:00`). Use crontab.guru to build the expression.
- Topics: the `topics` list in `feeds.yaml` (used for both tags and topic pages).
- AI model: `MODEL` in `src/summarize.py` (`claude-haiku-4-5` default;
  `claude-sonnet-4-6` for richer summaries). Confirm live IDs at
  https://platform.claude.com/docs/en/about-claude/models/overview.

## Verified vs. assumed

- [verified] feedparser works (tested); full pipeline tested end-to-end with the
  brain accumulating and de-duplicating across simulated runs.
- [verified] Claude model IDs (platform.claude.com Models overview, 2026).
- [verified] GitHub Actions: UTC, 5-min minimum, avoid top-of-hour.
- [verified] Claude Code Routines run unattended in Anthropic's cloud.
- [unverified] each source's exact RSS path (check_feeds confirms) and the Google
  News RSS URL format (widely used, not officially documented).
- [unverified] exact Microsoft Graph endpoints/scopes for the optional OneDrive
  mirror — confirm at build time if you add it.
