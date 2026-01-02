# MailMind - AI-Powered Email Auto-Responder

An intelligent email automation system that monitors your inbox and generates contextual AI-powered responses using OpenRouter API.

## Features

- 📧 **Automated Email Monitoring**: Continuously monitors IMAP inbox for new emails
- 🤖 **AI-Powered Responses**: Uses OpenRouter API (Claude, GPT, etc.) to generate professional, contextual replies
- 💾 **Database Tracking**: SQLite database to track emails and prevent duplicate responses
- 🔒 **Smart Filtering**: Automatically filters spam, newsletters, and automated emails
- ⏱️ **Configurable Delays**: Adds human-like delays between responses
- 🧵 **Thread Support**: Maintains email conversation threads
- 🔐 **Secure**: Supports SSL/TLS for IMAP and SMTP connections

## Prerequisites

- Python 3.7+
- Gmail account (or any IMAP/SMTP email provider)
- OpenRouter API key ([Get one here](https://openrouter.ai/))

## Installation

1. Clone the repository:
```bash
git clone <your-repo-url>
cd Mailmind
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure your settings:
```bash
python mailmind.py
```
This will create a `config.json` template. Edit it with your credentials:

```json
{
  "email": {
    "imap_server": "imap.gmail.com",
    "imap_port": 993,
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "email_address": "your.email@gmail.com",
    "password": "your_app_password",
    "use_ssl": true
  },
  "openrouter": {
    "api_key": "your_openrouter_api_key",
    "model": "anthropic/claude-3-sonnet"
  },
  "settings": {
    "signature": "Best regards,\\nYour Name",
    "response_delay": 300,
    "check_interval": 300
  }
}
```

### Gmail Setup

For Gmail, you need to:
1. Enable 2-factor authentication
2. Generate an [App Password](https://myaccount.google.com/apppasswords)
3. Use the app password in `config.json`

## Usage

### Test Connection
```bash
python testconnection.py
```

### Start Monitoring
```bash
python mailmind.py
```

### Run in Background (Linux/Mac)
```bash
nohup python mailmind.py &
```

## Configuration Options

| Setting | Description | Default |
|---------|-------------|---------|
| `response_delay` | Seconds to wait between responses | 300 (5 min) |
| `check_interval` | Seconds between inbox checks | 300 (5 min) |
| `signature` | Email signature to append | "" |
| `model` | OpenRouter model to use | claude-3-sonnet |

## Database

MailMind uses SQLite to store:
- **emails**: Incoming email metadata and content
- **responses**: Generated responses and AI usage stats
- **settings**: Application settings

Database file: `mailmind.db`

## Security Notes

⚠️ **Important**: 
- Never commit `config.json` with real credentials
- Use app-specific passwords, not your main email password
- The `.gitignore` excludes sensitive files by default

## Troubleshooting

**Connection Errors**: 
- Verify IMAP/SMTP settings for your email provider
- Check firewall/antivirus isn't blocking connections
- Ensure app password is correct

**AI Response Errors**:
- Verify OpenRouter API key is valid
- Check API quota/balance
- Review `mailmind.log` for detailed errors

## License

MIT License - Feel free to modify and use as needed.

## Author

Yaksi Shroff
