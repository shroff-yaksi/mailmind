<div align="center">

# 🧠 Mailmind

**Intelligent email automation — reads, thinks, replies. Locally.**

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-412991?style=for-the-badge&logo=openai&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-07405E?style=for-the-badge&logo=sqlite&logoColor=white)

</div>

---

## ✨ Overview

Mailmind connects to your inbox via IMAP, uses AI to draft context-aware replies, filters emails by smart rules, and sends responses automatically — all running locally with no cloud dependency and no subscriptions.

---

## 🔧 Features

| Feature | Description |
|---------|-------------|
| 📥 **IMAP Fetch** | Connects to Gmail and other providers via IMAP SSL |
| 🤖 **AI Replies** | Generates context-aware drafts using OpenAI |
| 🔍 **Smart Filters** | Blacklist / whitelist by sender, domain, keyword, or subject |
| ⏰ **Business Hours** | Only sends during configured working hours |
| 🔐 **Secure Secrets** | OS keychain via `keyring` with `.env` fallback |
| 🗄️ **Encrypted Backups** | Database encrypted with `cryptography.fernet` |
| 🌐 **Web Dashboard** | Flask UI on port 5050 — stats, email log, JSON API |
| 🧪 **Test Suite** | 49 tests — all passing |

---

## ⚙️ Tech Stack

| Layer | Tech |
|-------|------|
| Language | Python 3.10+ |
| Email (receive) | `imaplib` |
| Email (send) | `smtplib` |
| AI | OpenAI API |
| Secrets | `keyring` + `python-dotenv` |
| Encryption | `cryptography` (Fernet) |
| Dashboard | Flask |
| Database | SQLite |
| Testing | pytest |

---

## 🚀 Quick Start

```bash
pip install -r requirements.txt
cp .env.example .env   # fill in your credentials
python mailmind.py
```

**Dashboard:**
```bash
python dashboard.py
# → http://localhost:5050
# Default: admin / mailmind
```

**Run tests:**
```bash
pytest tests/ -v
# 49 passed ✓
```

---

## 🔐 Configuration

Add to `.env`:

```env
EMAIL_ADDRESS=your@gmail.com
EMAIL_PASSWORD=your_app_password
SMTP_HOST=smtp.gmail.com
DASHBOARD_USER=admin
DASHBOARD_PASS=yourpassword
```

> Sensitive values are stored in the OS keychain when `keyring` is available.

---

<div align="center">
<sub>Local AI email automation · No cloud · No subscriptions</sub>
</div>
