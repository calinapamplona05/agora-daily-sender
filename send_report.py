"""
Agora Research — Daily Market Report Sender
Finds the latest .pptx in reports/ and emails it to recipients via Gmail SMTP.
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
# Logging setup — prints timestamps so GitHub Actions logs are easy to read
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
GMAIL_RECIPIENTS = os.environ["GMAIL_RECIPIENTS"]   # comma-separated list of recipient emails

REPORTS_DIR = "reports"


# ---------------------------------------------------------------------------
# Helper: find the most recently modified .pptx in reports/
# ---------------------------------------------------------------------------
def find_latest_pptx(directory: str) -> str | None:
    pattern = os.path.join(directory, "*.pptx")
    files = glob.glob(pattern)
    if not files:
        return None
    return max(files, key=os.path.getmtime)


# ---------------------------------------------------------------------------
# Helper: build the email message
# ---------------------------------------------------------------------------
def build_email(sender: str, recipients: list[str], attachment_path: str) -> MIMEMultipart:
    today = date.today().strftime("%Y-%m-%d")
    filename = os.path.basename(attachment_path)

    msg = MIMEMultipart()
    msg["From"]    = sender
    msg["To"]      = ", ".join(recipients)
    msg["Subject"] = f"Agora Research | Daily Market Report — {today}"

    body = (
        f"Good morning,\n\n"
        f"Please find attached today's Agora Research Daily Market Report ({today}).\n\n"
        f"Best regards,\n"
        f"Agora Research Team"
    )
    msg.attach(MIMEText(body, "plain"))

    with open(attachment_path, "rb") as f:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(f.read())
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", f'attachment; filename="{filename}"')
    msg.attach(part)

    return msg


# ---------------------------------------------------------------------------
# Helper: send via Gmail SMTP with App Password
# ---------------------------------------------------------------------------
def send_email(msg: MIMEMultipart, sender: str, recipients: list[str]) -> None:
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender, GMAIL_PASSWORD)
        server.sendmail(sender, recipients, msg.as_string())


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
    pptx_path = find_latest_pptx(REPORTS_DIR)
    if not pptx_path:
        log.error(
            "No .pptx file found in '%s/'. "
            "Make sure Liam has pushed the report before 08:00 KST.",
            REPORTS_DIR,
        )
        # notify_slack(":warning: No .pptx found in reports/ — email NOT sent.")  # SLACK
        raise SystemExit(1)

    log.info("Report file found: %s", pptx_path)

    # 2. Parse recipients
    recipients = [r.strip() for r in GMAIL_RECIPIENTS.split(",") if r.strip()]
    if not recipients:
        log.error("GMAIL_RECIPIENTS is empty. Add at least one email address.")
        raise SystemExit(1)

    log.info("Sending to %d recipient(s): %s", len(recipients), ", ".join(recipients))

    # 3. Build and send
    msg = build_email(GMAIL_SENDER, recipients, pptx_path)
    try:
        send_email(msg, GMAIL_SENDER, recipients)
        log.info("Email sent successfully.")
        # notify_slack(f":white_check_mark: Daily report sent to {len(recipients)} recipient(s).")  # SLACK
    except Exception as exc:
        log.error("Failed to send email: %s", exc)
        # notify_slack(f":x: Email send failed: {exc}")  # SLACK
        raise SystemExit(1)

    log.info("=== Done ===")


if __name__ == "__main__":
    main()
