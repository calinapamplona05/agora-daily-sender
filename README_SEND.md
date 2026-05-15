# Agora Research — Daily Report Sender: Setup Guide

This guide walks you through the complete setup for the automated daily report email system.
No coding experience required — follow each step exactly.

---

## 1. Prerequisites

**On your Mac:**
- Python 3 installed (already confirmed ✅)
- Git installed (already confirmed ✅)
- A GitHub account at https://github.com

**Email:**
- A regular Gmail account
- 2-Step Verification must be ON (see Step 2)

---

## 2. Gmail Credential Setup

### Step 2a — Enable 2-Step Verification (if not already on)

1. Open: https://myaccount.google.com/security
2. Find "2-Step Verification" and click it
3. Follow the prompts to enable it
4. Come back here when done

### Step 2b — Create a Gmail App Password

> An App Password is a special 16-character code that lets apps send email
> on your behalf without needing your real password.

1. Open: https://myaccount.google.com/apppasswords
2. You may be asked to sign in again — do so
3. In the "App name" field, type: `Agora Daily Sender`
4. Click **Create**
5. Google shows you a 16-character password like: `abcd efgh ijkl mnop`
6. **Copy it immediately** (it will never be shown again)
7. Remove the spaces when you store it — it becomes: `abcdefghijklmnop`

Save this password somewhere safe temporarily — you will add it to GitHub Secrets in Step 4.

---

## 3. Create the GitHub Repo and Push Files

Open Terminal (press `Cmd + Space`, type "Terminal", press Enter).

Run these commands one by one. Copy and paste each line exactly:

```bash
# Go to the project folder
cd /Users/calina/agora-daily-sender

# Initialize git
git init

# Stage all files
git add .

# Make the first commit
git commit -m "Initial setup: Agora daily report sender"
```

Now go to https://github.com/new and create a repo named **exactly**:

```
agora-daily-sender
```

- Set it to **Public**
- Do NOT check "Add a README" (we already have files)
- Click **Create repository**

GitHub will show you a page with commands. Run the ones under
**"…or push an existing repository from the command line"**:

```bash
git remote add origin https://github.com/YOUR_USERNAME/agora-daily-sender.git
git branch -M main
git push -u origin main
```

Replace `YOUR_USERNAME` with your actual GitHub username.

---

## 4. GitHub Secrets — What to Add

Go to your repo on GitHub → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

Add these **3 secrets** exactly:

| Secret Name | Value | Where to find it |
|---|---|---|
| `GMAIL_SENDER` | Your Gmail address (e.g. `you@gmail.com`) | Your Gmail login |
| `GMAIL_PASSWORD` | The 16-char App Password from Step 2b (no spaces) | You copied it in Step 2b |
| `GMAIL_RECIPIENTS` | Comma-separated list of recipient emails (e.g. `a@b.com,c@d.com`) | Your team's email list |

**Which part of the script uses each secret:**
- `GMAIL_SENDER` → used as the "From" address and to log in to Gmail SMTP
- `GMAIL_PASSWORD` → used to authenticate with Gmail's SMTP server
- `GMAIL_RECIPIENTS` → the email addresses the report is sent to

---

## 5. Test Manually with workflow_dispatch

Instead of waiting until 08:00 KST, you can trigger the workflow right now:

1. Go to your repo on GitHub
2. Click the **Actions** tab
3. In the left sidebar, click **Send Daily Market Report**
4. Click the **Run workflow** button (top right of the table)
5. Leave branch as `main` and click the green **Run workflow** button

> **Important:** Before testing, make sure there is a `.pptx` file inside your `reports/` folder.
> You can add a dummy one for testing — see the local test in Step 7.

---

## 6. Verify It Worked — Finding the Logs

1. Go to your repo on GitHub → **Actions** tab
2. You'll see a row with the workflow run (green checkmark = success, red X = failure)
3. Click the row, then click **send-report** job
4. Expand each step to see the output
5. Look for the line: `Email sent successfully.`

If you see a red X, expand the **Send report email** step to read the error message.

---

## 7. Local Test (Optional but Recommended)

Run the script on your own Mac first to confirm it works before relying on GitHub Actions.

In Terminal:

```bash
# Go to the project folder
cd /Users/calina/agora-daily-sender

# Set the environment variables for this one test (replace values with yours)
export GMAIL_SENDER="you@gmail.com"
export GMAIL_PASSWORD="abcdefghijklmnop"
export GMAIL_RECIPIENTS="you@gmail.com"

# Run the script
python3 send_report.py
```

You should see output like:
```
2024-01-15 07:55:00  INFO  === Agora Research Daily Sender starting ===
2024-01-15 07:55:00  INFO  Report file found: reports/market_report.pptx
2024-01-15 07:55:00  INFO  Sending to 1 recipient(s): you@gmail.com
2024-01-15 07:55:02  INFO  Email sent successfully.
2024-01-15 07:55:02  INFO  === Done ===
```

Check your inbox — the email should arrive within a minute.

---

## 8. Adding Slack Later

When you're ready to add Slack notifications:

1. Create a Slack App at https://api.slack.com/apps and get a Bot Token starting with `xoxb-`
2. Add two more GitHub Secrets:
   - `SLACK_TOKEN` → the `xoxb-...` token
   - `SLACK_CHANNEL` → e.g. `#daily-reports`
3. In `send_report.py`, find all lines that say `# SLACK — uncomment` and remove the `#` at the start
4. In `.github/workflows/send_report.yml`, uncomment the two `SLACK_*` lines under `env:`
5. Commit and push

---

## 9. Troubleshooting — Top 5 Issues

### Issue 1: `SMTPAuthenticationError` — "Username and Password not accepted"
**Cause:** Wrong App Password, or 2-Step Verification is off.
**Fix:** Go back to Step 2b, generate a new App Password, update the `GMAIL_PASSWORD` secret.

### Issue 2: `No .pptx file found in 'reports/'`
**Cause:** Liam hasn't pushed the file yet, or pushed it to the wrong folder.
**Fix:** Make sure the file is inside the `reports/` folder (not the root of the repo), and that it ends in `.pptx`.

### Issue 3: Workflow doesn't run at 08:00 KST
**Cause:** GitHub Actions cron is UTC. 08:00 KST = 23:00 UTC the *previous* day. The cron is set correctly (`0 23 * * *`). Also note: GitHub sometimes delays scheduled runs by up to 15 minutes when servers are busy.
**Fix:** Wait up to 15 minutes. Use `workflow_dispatch` for testing.

### Issue 4: `KeyError: 'GMAIL_SENDER'` in the logs
**Cause:** GitHub Secret name doesn't match exactly (they are case-sensitive).
**Fix:** Go to repo Settings → Secrets → verify the name is exactly `GMAIL_SENDER` (all caps).

### Issue 5: Email arrives but has no attachment
**Cause:** The `.pptx` file was corrupted or zero bytes when pushed.
**Fix:** Check the file size in the `reports/` folder on GitHub. Re-push if needed.
