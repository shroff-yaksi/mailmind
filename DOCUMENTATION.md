# MailMind Documentation

This document provides detailed information about the MailMind API, troubleshooting common issues, use case examples, and email provider configurations.

---

## 1. API Documentation

### Data Structures

#### `EmailConfig`
Configuration for email server connections.
- `imap_server` (str): IMAP server address (e.g., `imap.gmail.com`).
- `imap_port` (int): IMAP server port (usually `993` for SSL).
- `smtp_server` (str): SMTP server address (e.g., `smtp.gmail.com`).
- `smtp_port` (int): SMTP server port (usually `587` for STARTTLS or `465` for SSL).
- `email_address` (str): Your email address.
- `password` (str): Your email password (preferably an App Password).
- `use_ssl` (bool): Whether to use SSL/TLS for connections.

#### `EmailMessage`
Represents an email message.
- `msg_id` (str): Unique identifier for the message.
- `sender` (str): Sender's email address or name.
- `subject` (str): Email subject line.
- `body` (str): Plain text body of the email.
- `timestamp` (datetime): When the email was received.
- `thread_id` (Optional[str]): Identifier for conversation threading.
- `is_replied` (bool): Whether a response has already been sent.

### Core Classes

#### `DatabaseManager`
Handles all interactions with the SQLite database.
- `save_email(email_msg: EmailMessage)`: Persists an email to the database.
- `mark_as_replied(msg_id: str)`: Updates an email record status to replied.
- `get_unreplied_emails()`: Retrieves a list of emails needing a response.

#### `OpenRouterClient`
Interface for generating AI responses via OpenRouter.
- `generate_response(email_content, sender, subject, context)`: Sends a prompt to the AI model and returns the response text and token usage.

#### `EmailProcessor`
The main engine for orchestrating email retrieval and response.
- `fetch_new_emails()`: Connects to IMAP and retrieves recent unread messages.
- `process_emails()`: Orchestrates the fetch-save-respond cycle.
- `start_monitoring(check_interval)`: Runs the processing loop at specific intervals.

---

## 2. Troubleshooting Guide

### Connection Issues
- **IMAP/SMTP Authentication Failed**: 
  - Ensure you are using an **App Password** for Gmail/Outlook, not your main account password.
  - Verify that IMAP access is enabled in your email provider's settings.
- **Connection Timed Out**:
  - Check if your firewall is blocking ports `993`, `587`, or `465`.
  - Ensure the server addresses are correct (e.g., `imap.gmail.com` vs. `pop.gmail.com`).

### AI & API Issues
- **Empty Responses**:
  - Check your OpenRouter balance/quota.
  - Verify your API key in the `.env` file.
  - Ensure the selected model is correctly spelled in `config.json` or `.env`.
- **Rate Limiting**:
  - If you see `429` errors, increase the `RESPONSE_DELAY` in your configuration to avoid hitting API limits.

### Database Issues
- **Duplicate Replied**:
  - If MailMind replies multiple times, ensure `mailmind.db` is writeable.
  - Check `mailmind.log` for database lock errors.
- **Corrupt Database**:
  - If the database becomes corrupt, you can safely delete `mailmind.db` and restart. It will re-index new emails from the last 24 hours.

---

## 3. Use Case Examples

### Case A: Executive Personal Assistant
**Goal**: Filter unimportant emails and acknowledge important ones.
- **Settings**:
  - `RESPONSE_DELAY`: 600 (10 minutes)
  - `OPENROUTER_MODEL`: `anthropic/claude-3-haiku`
  - **Prompt Modification**: "Act as a helpful executive assistant. Acknowledge the email and state that I will review it personally later today."

### Case B: 24/7 Customer Support
**Goal**: Instant acknowledgment for support tickets.
- **Settings**:
  - `RESPONSE_DELAY`: 30 (30 seconds)
  - `OPENROUTER_MODEL`: `openai/gpt-3.5-turbo`
  - **Template**: Use the `Support Request` template in `templates.md`.

### Case C: Freelance Inquiry Responder
**Goal**: Qualify leads and provide a portfolio link.
- **Settings**:
  - `EMAIL_SIGNATURE`: Includes your portfolio link.
  - **Context**: "If the email is about a new project, mention that I am currently taking on new clients for March."

---

## 4. Supported Email Providers

| Provider | IMAP Server | IMAP Port | SMTP Server | SMTP Port |
|----------|-------------|-----------|-------------|-----------|
| **Gmail** | `imap.gmail.com` | 993 | `smtp.gmail.com` | 587 / 465 |
| **Outlook/Hotmail** | `outlook.office365.com` | 993 | `smtp.office365.com` | 587 |
| **Yahoo Mail** | `imap.mail.yahoo.com` | 993 | `smtp.mail.yahoo.com` | 465 / 587 |
| **iCloud** | `imap.mail.me.com` | 993 | `smtp.mail.me.com` | 587 |
| **AOL** | `imap.aol.com` | 993 | `smtp.aol.com` | 465 |
| **Zoho Mail** | `imap.zoho.com` | 993 | `smtp.zoho.com` | 465 / 587 |

> **Note**: For most providers, you must use an **App Password** if Two-Factor Authentication (2FA) is enabled.
