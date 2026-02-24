# Mailmind — Intelligent Email Automation

> **Type:** Python CLI Tool · **Status:** Active · **Platform:** macOS / Linux

Mailmind is an intelligent email automation tool that reads your inbox, uses AI to draft context-aware replies, filters emails by rules, and sends responses automatically — all running locally with no cloud dependency.

---

## Features

| Feature | Description |
|---------|-------------|
| 📥 IMAP Fetch | Connects to Gmail (and other providers) via IMAP SSL |
| 🤖 AI Replies | Generates context-aware draft responses using OpenAI |
| 🔍 Smart Filtering | Blacklist/whitelist by sender, domain, keyword, subject |
| ⏰ Business Hours | Only sends during configured working hours |
| 🔐 Secrets Management | Credentials via OS keychain (`keyring`) with `.env` fallback |
| 🗄 Encrypted Backups | Database backups encrypted with `cryptography.fernet` |
| 🌐 Web Dashboard | Flask dashboard (port 5050) with stats, log, and JSON API |
| 🧪 Test Suite | 49 tests covering IMAP, SMTP, filters, and business hours |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.10+ |
| Email (IMAP) | `imaplib` |
| Email (SMTP) | `smtplib` |
| AI | OpenAI API |
| Secrets | `keyring` (OS keychain) + `python-dotenv` |
| Encryption | `cryptography` (Fernet) |
| Dashboard | Flask |
| Database | SQLite |
| Testing | `pytest` (49 tests, all passing) |

---

## Quick Start

```bash
pip install -r requirements.txt
cp .env.example .env   # fill in credentials
python mailmind.py
```

**Dashboard:**
```bash
python dashboard.py
# → http://localhost:5050  (default: admin / mailmind)
```

---

## Configuration

All sensitive values go in `.env` (or OS keychain via `keyring`):

```env
EMAIL_ADDRESS=your@gmail.com
EMAIL_PASSWORD=app_password_here
SMTP_HOST=smtp.gmail.com
DASHBOARD_USER=admin
DASHBOARD_PASS=yourpassword
```

---

## Test Suite

```bash
pytest tests/ -v
# 49 passed in ~0.7s
```

---

## Remaining

- Multi-provider testing (Outlook, Yahoo, Zoho)
- Multi-account parallel IMAP support

---

*Local AI email automation — no cloud, no subscriptions*
