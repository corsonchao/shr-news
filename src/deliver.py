"""Daily email via SMTP (no connector). Shows only NEW items from today's run."""
from __future__ import annotations
import datetime as dt
import html
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

_TAG_COLORS = {
    "drilling": "#b45309", "well construction": "#0369a1", "materials": "#7c3aed",
    "electronics": "#be123c", "sensors": "#047857", "subsurface mapping": "#1d4ed8",
}


def _tag(kw: str) -> str:
    color = _TAG_COLORS.get(kw, "#475569")
    return (f'<span style="background:{color};color:#fff;border-radius:10px;'
            f'padding:2px 9px;font-size:12px;margin:0 4px 4px 0;'
            f'display:inline-block;">{html.escape(kw)}</span>')


def _full_card(r: dict) -> str:
    """A HIGH-relevance item: full plain-language summary + tags."""
    tags = "".join(_tag(k) for k in r.get("keywords", []))
    return f"""
    <article style="border-bottom:1px solid #e2e8f0;padding:14px 0;">
      <a href="{html.escape(r['url'], quote=True)}" style="font-size:16px;
         font-weight:600;color:#0f172a;text-decoration:none;">
         &#9650; {html.escape(r['title'])}</a>
      <div style="color:#64748b;font-size:13px;margin:2px 0 6px;">
         {html.escape(r['source'])}</div>
      <p style="margin:0 0 8px;color:#334155;line-height:1.5;">
         {html.escape(r.get('plain_summary',''))}</p>
      <div>{tags}</div>
    </article>"""


def _title_row(r: dict) -> str:
    """A MEDIUM-relevance item: title + source as a compact link only."""
    topics = ", ".join(r.get("keywords", []))
    topics_html = (f' <span style="color:#94a3b8;">&middot; {html.escape(topics)}</span>'
                   if topics else "")
    return f"""
    <li style="margin:0 0 8px;line-height:1.4;">
      <a href="{html.escape(r['url'], quote=True)}"
         style="color:#0f172a;font-weight:600;text-decoration:none;">
         {html.escape(r['title'])}</a>
      <span style="color:#64748b;font-size:13px;"> &mdash; {html.escape(r['source'])}</span>
      {topics_html}
    </li>"""


def build_email_html(new_records: list[dict], site_url: str = "",
                     period_label: str = "") -> str:
    """Weekly digest. HIGH items get full summaries; MEDIUM items get title-only
    rows. (LOW items are already dropped upstream in summarize_all.)"""
    today = dt.date.today().isoformat()
    label = period_label or f"Week ending {today}"

    highs = [r for r in new_records if r.get("relevance") == "high"]
    mediums = [r for r in new_records if r.get("relevance") == "medium"]

    if not new_records:
        body = "<p>No new superhot-rock items this week.</p>"
    else:
        body = ""
        # HIGHLIGHTS — full summaries
        if highs:
            body += ('<h2 style="font-size:15px;text-transform:uppercase;'
                     'letter-spacing:1px;color:#b45309;margin:18px 0 4px;">'
                     f'Highlights ({len(highs)})</h2>')
            body += "".join(_full_card(r) for r in highs)
        # ALSO THIS WEEK — titles only
        if mediums:
            body += ('<h2 style="font-size:15px;text-transform:uppercase;'
                     'letter-spacing:1px;color:#475569;margin:26px 0 6px;">'
                     f'Also this week ({len(mediums)})</h2>')
            body += ('<ul style="padding-left:18px;margin:0;">'
                     + "".join(_title_row(r) for r in mediums) + "</ul>")

    footer = ""
    if site_url:
        footer = (f'<p style="margin-top:24px;"><a href="{html.escape(site_url,quote=True)}">'
                  f'Browse the full knowledge base &rarr;</a></p>')

    return f"""<!doctype html><html><body style="font-family:system-ui,sans-serif;
      max-width:680px;margin:0 auto;padding:20px;color:#0f172a;">
      <h1 style="margin-bottom:2px;">Superhot Rock Geothermal &mdash; Weekly Digest</h1>
      <div style="color:#64748b;margin-bottom:8px;">{label} &middot;
         {len(new_records)} item(s) &middot; {len(highs)} highlight(s)</div>
      {body}{footer}
    </body></html>"""


def send_email(html_body: str) -> None:
    """Required env: SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, MAIL_TO.
    Gmail: host=smtp.gmail.com port=587, SMTP_PASS = an App Password."""
    host = os.environ["SMTP_HOST"]
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ["SMTP_USER"]
    password = os.environ["SMTP_PASS"]
    # MAIL_TO may be a single address or several separated by commas, e.g.
    #   "a@x.com, b@y.com, c@z.com"
    # We split on commas and strip whitespace so stray spaces don't break it.
    recipients = [addr.strip() for addr in os.environ["MAIL_TO"].split(",")
                  if addr.strip()]

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"SHR Geothermal Digest — {dt.date.today().isoformat()}"
    msg["From"] = user
    # Recipients go in Bcc, NOT To, so nobody sees the others' addresses.
    # We deliberately do not add the addresses to any visible header. The "To"
    # header is set to the sender itself so the message isn't headerless (some
    # providers flag mail with no To: line as spam).
    msg["To"] = user
    # NOTE: we intentionally do NOT set msg["Bcc"] — if it were added to the
    # message headers it could be exposed. Instead we keep the recipient list
    # out of the message entirely and pass it only to the delivery call below,
    # which is what actually makes Bcc private.
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(host, port) as server:
        server.starttls()
        server.login(user, password)
        # Deliver to every recipient via the envelope (to_addrs) only. Because
        # these addresses appear in no visible header, each recipient sees only
        # the sender in "To" and cannot see the other recipients — true Bcc.
        server.send_message(msg, from_addr=user, to_addrs=recipients)
