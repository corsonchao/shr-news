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


def build_email_html(new_records: list[dict], site_url: str = "") -> str:
    today = dt.date.today().isoformat()
    if not new_records:
        body = "<p>No new superhot-rock items today.</p>"
    else:
        rows = []
        for r in new_records:
            tags = "".join(_tag(k) for k in r.get("keywords", []))
            star = " ⭐" if r.get("highlight") else ""
            rows.append(f"""
            <article style="border-bottom:1px solid #e2e8f0;padding:14px 0;">
              <a href="{html.escape(r['url'], quote=True)}" style="font-size:16px;
                 font-weight:600;color:#0f172a;text-decoration:none;">
                 {html.escape(r['title'])}{star}</a>
              <div style="color:#64748b;font-size:13px;margin:2px 0 6px;">
                 {html.escape(r['source'])} &middot; {html.escape(r.get('relevance',''))}</div>
              <p style="margin:0 0 8px;color:#334155;line-height:1.5;">
                 {html.escape(r.get('plain_summary',''))}</p>
              <div>{tags}</div>
            </article>""")
        body = "\n".join(rows)

    footer = ""
    if site_url:
        footer = (f'<p style="margin-top:18px;"><a href="{html.escape(site_url,quote=True)}">'
                  f'Browse the full knowledge base &rarr;</a></p>')

    return f"""<!doctype html><html><body style="font-family:system-ui,sans-serif;
      max-width:680px;margin:0 auto;padding:20px;color:#0f172a;">
      <h1 style="margin-bottom:2px;">Superhot Rock Geothermal Digest</h1>
      <div style="color:#64748b;margin-bottom:16px;">{today} &middot;
         {len(new_records)} new item(s)</div>
      {body}{footer}
    </body></html>"""


def send_email(html_body: str) -> None:
    """Required env: SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, MAIL_TO.
    Gmail: host=smtp.gmail.com port=587, SMTP_PASS = an App Password."""
    host = os.environ["SMTP_HOST"]
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ["SMTP_USER"]
    password = os.environ["SMTP_PASS"]
    to_addr = os.environ["MAIL_TO"]

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"SHR Geothermal Digest — {dt.date.today().isoformat()}"
    msg["From"] = user
    msg["To"] = to_addr
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(host, port) as server:
        server.starttls()
        server.login(user, password)
        server.send_message(msg)
