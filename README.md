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
- 📝 **Email Templates**: Pre-built templates for common responses
- 🚫 **Blacklist/Whitelist**: Flexible sender filtering with domain and keyword support
- 🔄 **Retry Logic**: Automatic retry with exponential backoff for network failures
- ✅ **Input Validation**: Email validation and text sanitization for security
- 🐳 **Docker Support**: Ready-to-deploy Docker and docker-compose configurations
- 📊 **Test Coverage**: 34 unit tests with 45% code coverage
- 🛠️ **Development Tools**: Makefile, linting, formatting, and type checking

## Prerequisites

- Python 3.7+
- Gmail account (or any IMAP/SMTP email provider)
- OpenRouter API key ([Get one here](https://openrouter.ai/))

## Installation

1. Clone the repository:
```bash
git clone <your-repo-url>
cd mailmind
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your credentials
nano .env  # or use your preferred editor
```

4. Configure your `.env` file with the following required settings:

```bash
# Email Configuration
EMAIL_ADDRESS=your.email@gmail.com
EMAIL_PASSWORD=your_app_password_here

# IMAP Settings
IMAP_SERVER=imap.gmail.com
IMAP_PORT=993

# SMTP Settings
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587

# SSL/TLS
USE_SSL=true

# OpenRouter API Configuration
OPENROUTER_API_KEY=your_openrouter_api_key_here
OPENROUTER_MODEL=mistralai/mistral-7b-instruct:free

# Application Settings
EMAIL_SIGNATURE=Your Name
RESPONSE_DELAY=300
CHECK_INTERVAL=300
```

### Gmail Setup

For Gmail, you need to:
1. Enable 2-factor authentication
2. Generate an [App Password](https://myaccount.google.com/apppasswords)
3. Use the app password in your `.env` file (not your regular Gmail password)

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
- **Never commit `.env` file to version control** - it contains your credentials
- The `.env` file is automatically excluded by `.gitignore`
- Use app-specific passwords, not your main email password
- Keep your OpenRouter API key secure
- Regularly rotate your credentials
- The `config.json` file is now safe to commit (contains no credentials)

## Deployment

### Docker Deployment (Recommended)

```bash
# Quick start with docker-compose
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed deployment instructions including:
- Docker deployment
- Systemd service setup
- Monitoring and backups
- Troubleshooting

### Email Filtering

**Blacklist Configuration** (`blacklist.txt`):
- Block specific email addresses
- Block entire domains
- Block keywords in sender address
- Block subject line keywords

**Whitelist Configuration** (`whitelist.txt`):
- Always process emails from specific addresses
- Always process emails from specific domains
- Whitelist takes precedence over blacklist

**Email Templates** (`templates.md`):
- Pre-built templates for common scenarios
- Out of office, meeting requests, support tickets
- Customizable with variables

## Troubleshooting

**Connection Errors**: 
- Verify IMAP/SMTP settings for your email provider
- Check firewall/antivirus isn't blocking connections
- Ensure app password is correct

**AI Response Errors**:
- Verify OpenRouter API key is valid
- Check API quota/balance
- Review `mailmind.log` for detailed errors

## Development

### Running Tests

```bash
# Run all tests
make test

# Run tests with coverage
make test-cov

# Run specific test file
pytest tests/test_email_parsing.py -v
```

### Code Quality

```bash
# Format code
make format

# Check formatting
make format-check

# Run linting
make lint

# Type checking
make type-check

# Run all checks
make all
```

### Project Structure

```
mailmind/
├── mailmind.py          # Main application
├── testconnection.py    # Connection testing utility
├── .env                 # Environment variables (not in git)
├── .env.example         # Environment template
├── config.json          # Non-sensitive configuration
├── requirements.txt     # Python dependencies
├── pyproject.toml       # Tool configuration
├── .flake8              # Linting configuration
├── Makefile             # Development commands
└── tests/               # Test suite
    ├── conftest.py      # Test fixtures
    ├── test_database.py
    ├── test_email_parsing.py
    └── test_error_handling.py
```

### Code Coverage

Current test coverage: **44%**

Areas with good coverage:
- Email validation and sanitization
- Retry logic and error handling
- Database operations
- Email parsing and filtering

Areas needing more tests:
- IMAP/SMTP integration
- End-to-end email processing
- AI response generation

## License

MIT License - Feel free to modify and use as needed.

## Author

Yaksi Shroff
