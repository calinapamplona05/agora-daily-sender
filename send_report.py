"""
Agora Research — Daily Market Report Sender
Finds the latest .pdf in reports/ and sends each recipient their own individual email.
Each person only sees their own address in TO — nobody sees anyone else.
Credentials are read from environment variables (set as GitHub Secrets).
"""

import os
import glob
import json
import smtplib
import logging
import urllib.request
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration — all values come from environment variables / GitHub Secrets
# ---------------------------------------------------------------------------
GMAIL_SENDER     = os.environ["GMAIL_SENDER"]       # your Gmail address
GMAIL_PASSWORD   = os.environ["GMAIL_PASSWORD"]     # Gmail App Password (16 chars, no spaces)
GMAIL_RECIPIENTS = os.environ["GMAIL_RECIPIENTS"]   # all recipients, comma-separated — each gets their own individual email

LINKEDIN_ACCESS_TOKEN = os.environ.get("LINKEDIN_ACCESS_TOKEN", "")
LINKEDIN_ORG_ID       = os.environ.get("LINKEDIN_ORG_ID", "")

REPORTS_DIR = "reports"


# ---------------------------------------------------------------------------
# Helper: find the most recently modified .pdf in reports/
# ---------------------------------------------------------------------------
def find_latest_pdf(directory: str) -> str | None:
    pattern = os.path.join(directory, "*.pdf")
    files = glob.glob(pattern)
    if not files:
        return None
    return max(files, key=os.path.getmtime)


# ---------------------------------------------------------------------------
# Helper: build a personal email addressed to one recipient only
# ---------------------------------------------------------------------------
def build_email(sender: str, recipient: str, attachment_path: str) -> MIMEMultipart:
    today = date.today().strftime("%Y-%m-%d")
    filename = os.path.basename(attachment_path)

    msg = MIMEMultipart()
    msg["From"]    = sender
    msg["To"]      = recipient          # only this person's address — no one else visible
    msg["Subject"] = f"Agora Research | Daily Market Report — {today}"

    body = (
        f"Good morning,\n\n"
        f"Please find attached today's Agora Research Daily Market Report ({today}).\n\n"
        f"Best regards,\n"
        f"Agora Research Team"
    )
    msg.attach(MIMEText(body, "plain"))

    with open(attachment_path, "rb") as f:
        part = MIMEBase("application", "pdf")
        part.set_payload(f.read())
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", f'attachment; filename="{filename}"')
    msg.attach(part)

    return msg


# ---------------------------------------------------------------------------
# Helper: send one email to one recipient via Gmail SMTP
# ---------------------------------------------------------------------------
def send_email(msg: MIMEMultipart, sender: str, recipient: str) -> None:
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender, GMAIL_PASSWORD)
        server.sendmail(sender, [recipient], msg.as_string())


# ---------------------------------------------------------------------------
# LinkedIn — post a daily announcement to the Agora Research company page
# ---------------------------------------------------------------------------
def post_linkedin(pdf_path: str) -> None:
    if not LINKEDIN_ACCESS_TOKEN or not LINKEDIN_ORG_ID:
        log.warning("LinkedIn secrets not set — skipping LinkedIn post.")
        return

    today = date.today().strftime("%Y-%m-%d")
    message = (
        f"📊 Agora Research Daily Market Report — {today}\n\n"
        f"Today's market report has been distributed to subscribers.\n\n"
        f"#AgoraResearch #MarketReport #Finance"
    )

    data = json.dumps({
        "author": f"urn:li:organization:{LINKEDIN_ORG_ID}",
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": message},
                "shareMediaCategory": "NONE",
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
        },
    }).encode()

    req = urllib.request.Request(
        "https://api.linkedin.com/v2/ugcPosts",
        data=data,
        headers={
            "Authorization": f"Bearer {LINKEDIN_ACCESS_TOKEN}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
        },
    )
    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read())
            log.info("LinkedIn post published: %s", result.get("id", "ok"))
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        log.error("LinkedIn post failed (%s): %s", e.code, body)


# ---------------------------------------------------------------------------
# SLACK — uncomment and fill in token when ready
# ---------------------------------------------------------------------------
# SLACK_TOKEN   = os.environ.get("SLACK_TOKEN", "")
# SLACK_CHANNEL = os.environ.get("SLACK_CHANNEL", "#daily-reports")
#
# def notify_slack(message: str) -> None:
#     """Post a short status message to Slack."""
#     import urllib.request, json
#     payload = json.dumps({"channel": SLACK_CHANNEL, "text": message}).encode()
#     req = urllib.request.Request(
#         "https://slack.com/api/chat.postMessage",
#         data=payload,
#         headers={
#             "Authorization": f"Bearer {SLACK_TOKEN}",
#             "Content-Type": "application/json",
#         },
#     )
#     with urllib.request.urlopen(req) as resp:
#         result = json.loads(resp.read())
#         if not result.get("ok"):
#             log.warning("Slack notification failed: %s", result.get("error"))
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    log.info("=== Agora Research Daily Sender starting ===")

    # 1. Find the report file
    pdf_path = find_latest_pdf(REPORTS_DIR)
    if not pdf_path:
        log.error(
            "No .pdf file found in '%s/'. "
            "Make sure Liam has pushed the report before 08:00 KST.",
            REPORTS_DIR,
        )
        # notify_slack(":warning: No .pdf found in reports/ — email NOT sent.")  # SLACK
        raise SystemExit(1)

    log.info("Report file found: %s", pdf_path)

    # 2. Parse recipients — every person gets their own individual email
    recipients = [r.strip() for r in GMAIL_RECIPIENTS.split(",") if r.strip()]

    if not recipients:
        log.error("GMAIL_RECIPIENTS is empty. Add at least one email address.")
        raise SystemExit(1)

    log.info("Sending individual emails to %d recipient(s).", len(recipients))

    # 3. Send one email per recipient — each person only sees their own address
    failed = []
    for recipient in recipients:
        try:
            msg = build_email(GMAIL_SENDER, recipient, pdf_path)
            send_email(msg, GMAIL_SENDER, recipient)
            log.info("  ✓ Sent to %s", recipient)
        except Exception as exc:
            log.error("  ✗ Failed to send to %s: %s", recipient, exc)
            failed.append(recipient)

    if failed:
        log.error("Failed to send to: %s", ", ".join(failed))
        # notify_slack(f":x: Email failed for: {', '.join(failed)}")  # SLACK
        raise SystemExit(1)

    # notify_slack(f":white_check_mark: Daily report sent to {len(recipients)} recipient(s).")  # SLACK

    # 4. Post to LinkedIn company page
    post_linkedin(pdf_path)

    log.info("=== Done ===")


if __name__ == "__main__":
    main()
