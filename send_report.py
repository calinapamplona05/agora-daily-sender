"""
Agora Research — Daily Market Report Sender
Finds the latest .pdf in reports/ and emails it to recipients via Gmail SMTP.
TO: main recipient (visible). BCC: all others (hidden from each other).
Credentials are read from environment variables (set as GitHub Secrets).
"""

import os
import glob
import smtplib
import logging
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
GMAIL_RECIPIENTS = os.environ["GMAIL_RECIPIENTS"]   # TO field — main recipient(s), comma-separated
GMAIL_BCC        = os.environ.get("GMAIL_BCC", "")  # BCC field — hidden recipients, comma-separated

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
# Helper: build the email message
# ---------------------------------------------------------------------------
def build_email(
    sender: str,
    recipients: list[str],
    bcc: list[str],
    attachment_path: str,
) -> MIMEMultipart:
    today = date.today().strftime("%Y-%m-%d")
    filename = os.path.basename(attachment_path)

    msg = MIMEMultipart()
    msg["From"]    = sender
    msg["To"]      = ", ".join(recipients)
    msg["Subject"] = f"Agora Research | Daily Market Report — {today}"
    if bcc:
        msg["Bcc"] = ", ".join(bcc)

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
# Helper: send via Gmail SMTP with App Password
# ---------------------------------------------------------------------------
def send_email(
    msg: MIMEMultipart,
    sender: str,
    recipients: list[str],
    bcc: list[str],
) -> None:
    all_addresses = recipients + bcc
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender, GMAIL_PASSWORD)
        server.sendmail(sender, all_addresses, msg.as_string())


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

    # 2. Parse TO and BCC
    recipients = [r.strip() for r in GMAIL_RECIPIENTS.split(",") if r.strip()]
    bcc        = [b.strip() for b in GMAIL_BCC.split(",") if b.strip()]

    if not recipients:
        log.error("GMAIL_RECIPIENTS is empty. Add at least one email address.")
        raise SystemExit(1)

    log.info("TO  (%d): %s", len(recipients), ", ".join(recipients))
    if bcc:
        log.info("BCC (%d): %s", len(bcc), ", ".join(bcc))

    # 3. Build and send
    msg = build_email(GMAIL_SENDER, recipients, bcc, pdf_path)
    try:
        send_email(msg, GMAIL_SENDER, recipients, bcc)
        log.info("Email sent successfully.")
        # notify_slack(f":white_check_mark: Daily report sent to {len(recipients)} recipient(s) + {len(bcc)} BCC.")  # SLACK
    except Exception as exc:
        log.error("Failed to send email: %s", exc)
        # notify_slack(f":x: Email send failed: {exc}")  # SLACK
        raise SystemExit(1)

    log.info("=== Done ===")


if __name__ == "__main__":
    main()
