#!/usr/bin/env python3
"""
MailMind: Automated Email Responder
A sophisticated email automation system with AI-powered responses using OpenRouter API.
"""

import os
import json
import time
import logging
import imaplib
import smtplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Callable, Any
from dataclasses import dataclass
import requests
from threading import Lock
import sqlite3
from contextlib import contextmanager
import re
from html import unescape
import hashlib
from dotenv import load_dotenv
from functools import wraps


import logging.handlers

# Create logs directory if it doesn't exist
os.makedirs("logs", exist_ok=True)

# Configure logging
log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
log_level = logging.INFO

# File handler for daily rotation
file_handler = logging.handlers.TimedRotatingFileHandler(
    filename=os.path.join("logs", "mailmind.log"),
    when="midnight",
    interval=1,
    backupCount=30,
    encoding="utf-8",
)
file_handler.setFormatter(logging.Formatter(log_format))

# Console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter(log_format))

# Setup root logger
root_logger = logging.getLogger()
root_logger.setLevel(log_level)
root_logger.addHandler(file_handler)
root_logger.addHandler(console_handler)

logger = logging.getLogger(__name__)


# Retry decorator with exponential backoff
def retry_with_backoff(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: Tuple = (Exception,),
) -> Callable:
    """
    Decorator for retrying functions with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        backoff_factor: Multiplier for delay after each retry
        exceptions: Tuple of exceptions to catch and retry
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            delay = initial_delay
            last_exception = None
            func_name = getattr(func, "__name__", "unknown_function")

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_retries} failed for {func_name}: {e}. "
                            f"Retrying in {delay:.1f}s..."
                        )
                        time.sleep(delay)
                        delay *= backoff_factor
                    else:
                        logger.error(
                            f"All {max_retries} retry attempts failed for {func_name}: {e}"
                        )

            raise last_exception

        return wrapper

    return decorator


def validate_email(email_address: str) -> bool:
    """
    Validate email address format.

    Args:
        email_address: Email address to validate

    Returns:
        True if valid, False otherwise
    """
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return re.match(pattern, email_address) is not None


def sanitize_text(text: str, max_length: int = 10000) -> str:
    """
    Sanitize text input by removing potentially harmful content.

    Args:
        text: Text to sanitize
        max_length: Maximum allowed length

    Returns:
        Sanitized text
    """
    if not text:
        return ""

    # Truncate to max length
    text = text[:max_length]

    # Remove null bytes
    text = text.replace("\x00", "")

    # Remove control characters except newlines and tabs
    text = "".join(char for char in text if char.isprintable() or char in "\n\t")

    return text.strip()


@dataclass
class EmailConfig:
    """Email configuration settings"""

    imap_server: str
    imap_port: int
    smtp_server: str
    smtp_port: int
    email_address: str
    password: str
    use_ssl: bool = True


@dataclass
class Attachment:
    """Email attachment metadata"""

    filename: str
    content_type: str
    size: int
    file_path: str


@dataclass
class EmailMessage:
    """Email message data structure"""

    msg_id: str
    sender: str
    subject: str
    body: str
    timestamp: datetime
    thread_id: Optional[str] = None
    is_replied: bool = False
    attachments: List[Attachment] = None
    id: Optional[int] = None

    def __post_init__(self):
        if self.attachments is None:
            self.attachments = []


class DatabaseManager:
    """Database manager for storing email data and responses"""

    def __init__(self, db_path: str = "mailmind.db"):
        """
        Initialize the DatabaseManager.

        Args:
            db_path: Path to the SQLite database file. Defaults to "mailmind.db".
        """
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Initialize database tables"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Emails table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS emails (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    msg_id TEXT UNIQUE,
                    sender TEXT,
                    subject TEXT,
                    body TEXT,
                    timestamp TEXT,
                    thread_id TEXT,
                    is_replied BOOLEAN DEFAULT 0,
                    category TEXT,
                    sentiment TEXT,
                    priority TEXT DEFAULT 'Medium',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Responses table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS responses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email_id INTEGER,
                    response_text TEXT,
                    sent_at TEXT,
                    model_used TEXT,
                    tokens_used INTEGER,
                    ab_version TEXT,
                    FOREIGN KEY (email_id) REFERENCES emails (id)
                )
            """
            )

            # AI Cache table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS ai_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content_hash TEXT UNIQUE,
                    response_text TEXT,
                    category TEXT,
                    sentiment TEXT,
                    priority TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Settings table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """
            )

            # Attachments table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS attachments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email_id INTEGER,
                    filename TEXT,
                    content_type TEXT,
                    size INTEGER,
                    file_path TEXT,
                    FOREIGN KEY (email_id) REFERENCES emails (id)
                )
            """
            )

            conn.commit()

    @contextmanager
    def get_connection(self):
        """
        Context manager for database connections, ensuring proper closure.

        Yields:
            sqlite3.Connection: A connection object to the SQLite database.
        """
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
        finally:
            conn.close()

    def save_email(self, email_msg: EmailMessage) -> int:
        """
        Save an email message to the database, including any attachments.

        Args:
            email_msg: The EmailMessage object to save.

        Returns:
            int: The ID of the inserted or replaced email row.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO emails
                (msg_id, sender, subject, body, timestamp, thread_id, is_replied, category, sentiment, priority)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    email_msg.msg_id,
                    email_msg.sender,
                    email_msg.subject,
                    email_msg.body,
                    email_msg.timestamp.isoformat(),
                    email_msg.thread_id,
                    email_msg.is_replied,
                    getattr(email_msg, "category", "Other"),
                    getattr(email_msg, "sentiment", "Neutral"),
                    getattr(email_msg, "priority", "Medium"),
                ),
            )
            email_id = cursor.lastrowid
            email_msg.id = email_id

            # Save attachments
            if email_msg.attachments:
                for att in email_msg.attachments:
                    cursor.execute(
                        """
                        INSERT INTO attachments
                        (email_id, filename, content_type, size, file_path)
                        VALUES (?, ?, ?, ?, ?)
                    """,
                        (email_id, att.filename, att.content_type, att.size, att.file_path),
                    )

            conn.commit()
            return email_id

    def mark_as_replied(self, msg_id: str):
        """
        Mark a specific email as replied in the database.

        Args:
            msg_id: The unique message ID of the email to update.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE emails SET is_replied = 1 WHERE msg_id = ?", (msg_id,))
            conn.commit()

    def get_unreplied_emails(self) -> List[EmailMessage]:
        """
        Get unreplied emails from database with their attachments.

        Returns:
            List[EmailMessage]: A list of EmailMessage objects.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, msg_id, sender, subject, body, timestamp, thread_id, is_replied
                FROM emails WHERE is_replied = 0
                ORDER BY timestamp ASC
            """
            )

            emails = []
            for row in cursor.fetchall():
                email_id, msg_id, sender, subject, body, timestamp_str, thread_id, is_replied = row

                # Fetch attachments for this email
                cursor.execute(
                    """
                    SELECT filename, content_type, size, file_path
                    FROM attachments WHERE email_id = ?
                """,
                    (email_id,),
                )

                attachments = []
                for att_row in cursor.fetchall():
                    attachments.append(
                        Attachment(
                            filename=att_row[0],
                            content_type=att_row[1],
                            size=att_row[2],
                            file_path=att_row[3],
                        )
                    )

                emails.append(
                    EmailMessage(
                        msg_id=msg_id,
                        sender=sender,
                        subject=subject,
                        body=body,
                        timestamp=datetime.fromisoformat(timestamp_str),
                        thread_id=thread_id,
                        is_replied=bool(is_replied),
                        attachments=attachments,
                        id=email_id,
                    )
                )
            return emails

    def get_thread_history(self, thread_id: str) -> List[EmailMessage]:
        """
        Retrieve all emails belonging to a specific thread.

        Args:
            thread_id: The ID of the conversation thread.

        Returns:
            List[EmailMessage]: A list of emails in the thread, ordered by timestamp.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT msg_id, sender, subject, body, timestamp, thread_id, is_replied
                FROM emails WHERE thread_id = ? OR msg_id = ?
                ORDER BY timestamp ASC
            """,
                (thread_id, thread_id),
            )

            history = []
            for row in cursor.fetchall():
                history.append(
                    EmailMessage(
                        msg_id=row[0],
                        sender=row[1],
                        subject=row[2],
                        body=row[3],
                        timestamp=datetime.fromisoformat(row[4]),
                        thread_id=row[5],
                        is_replied=bool(row[6]),
                    )
                )
            return history


class OpenRouterClient:
    """OpenRouter API client for AI responses"""

    def __init__(self, api_key: str, model: str = "mistralai/mistral-7b-instruct:free"):
        """
        Initialize the OpenRouterClient.

        Args:
            api_key: The OpenRouter API key.
            model: The AI model to use for generating responses. Defaults to Mistral 7B.
        """
        self.api_key = api_key
        self.model = model
        self.base_url = "https://openrouter.ai/api/v1"
        self.session = requests.Session()
        self.session.headers.update(
            {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        )

    @retry_with_backoff(
        max_retries=3,
        initial_delay=1.0,
        exceptions=(requests.exceptions.Timeout, requests.exceptions.ConnectionError),
    )
    def _make_api_request(self, prompt: str, max_tokens: int) -> Dict:
        """Make API request with retry logic and rate limit awareness"""
        # Simple rate limit: ensure at least 1 second between requests
        if hasattr(self, "_last_request_time"):
            elapsed = time.time() - self._last_request_time
            if elapsed < 1.0:
                time.sleep(1.0 - elapsed)
        
        response = self.session.post(
            f"{self.base_url}/chat/completions",
            json={
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a professional email assistant. Generate concise, helpful, and contextually appropriate email responses. Be polite, professional, and direct.",
                    },
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": max_tokens,
                "temperature": 0.7,
            },
            timeout=30,
        )
        self._last_request_time = time.time()
        response.raise_for_status()
        return response.json()

    def generate_response(
        self,
        email_content: str,
        sender: str,
        subject: str,
        context: str = "",
        max_tokens: int = 500,
        available_templates: List[str] = None,
    ) -> Tuple[str, int, Optional[str], Dict]:
        """
        Generate AI response with sentiment, category, and priority analysis.
        
        Returns:
            Tuple[str, int, Optional[str], Dict]: (response, tokens, template, analysis)
        """
        # 1. Caching logic (Performance)
        content_hash = hashlib.md5(f"{subject}{email_content}".encode()).hexdigest()
        cached = self._get_cached_response(content_hash)
        if cached:
            logger.info("Using cached AI response")
            return cached["response_text"], 0, None, {
                "category": cached["category"],
                "sentiment": cached["sentiment"],
                "priority": cached["priority"]
            }

        try:
            prompt = self._build_prompt(email_content, sender, subject, context, available_templates)
            data = self._make_api_request(prompt, max_tokens)
            content = data["choices"][0]["message"]["content"]
            tokens = data.get("usage", {}).get("total_tokens", 0)

            # Extract structured data from AI (assuming AI follows requirements)
            analysis = self._parse_ai_analysis(content)
            
            # Clean response text
            clean_response = self._cleanup_response(content, analysis)

            # Cache the result
            self._cache_response(content_hash, clean_response, analysis)

            template_used = None
            if available_templates:
                for t_name in available_templates:
                    if f"USE_TEMPLATE: {t_name}" in ai_response:
                        template_used = t_name
                        break

            return clean_response, tokens, template_used, analysis

        except Exception as e:
            logger.error(f"AI error: {e}")
            return self._generate_fallback_response(subject), 0, None, {"category": "Other", "sentiment": "Neutral", "priority": "Medium"}

    def _parse_ai_analysis(self, content: str) -> Dict:
        """Extract category, sentiment, and priority from AI response blocks."""
        analysis = {"category": "Other", "sentiment": "Neutral", "priority": "Medium"}
        try:
            patterns = {
                "category": r"CATEGORY:\s*(\w+)",
                "sentiment": r"SENTIMENT:\s*(\w+)",
                "priority": r"PRIORITY:\s*(\w+)"
            }
            for key, pattern in patterns.items():
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    analysis[key] = match.group(1).capitalize()
        except:
            pass
        return analysis

    def _cleanup_response(self, content: str, analysis: Dict) -> str:
        """Remove metadata blocks from final response text."""
        clean = content
        for key in ["CATEGORY", "SENTIMENT", "PRIORITY", "USE_TEMPLATE"]:
            clean = re.sub(rf"{key}:.*?\n", "", clean, flags=re.IGNORECASE)
        return clean.strip()

    def _get_cached_response(self, content_hash: str) -> Optional[Dict]:
        """Retrieve cached response from database."""
        db = sqlite3.connect("mailmind.db")
        try:
            cursor = db.cursor()
            cursor.execute("SELECT response_text, category, sentiment, priority FROM ai_cache WHERE content_hash = ?", (content_hash,))
            row = cursor.fetchone()
            if row:
                return {"response_text": row[0], "category": row[1], "sentiment": row[2], "priority": row[3]}
        finally:
            db.close()
        return None

    def _cache_response(self, content_hash: str, response: str, analysis: Dict):
        """Save AI response to cache table."""
        db = sqlite3.connect("mailmind.db")
        try:
            cursor = db.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO ai_cache (content_hash, response_text, category, sentiment, priority) VALUES (?, ?, ?, ?, ?)",
                (content_hash, response, analysis["category"], analysis["sentiment"], analysis["priority"])
            )
            db.commit()
        finally:
            db.close()

    def _build_prompt(self, email_content: str, sender: str, subject: str, context: str, templates: List[str] = None) -> str:
        """Build AI prompt for email response"""
        template_hint = ""
        if templates:
            template_hint = f"\nAvailable templates: {', '.join(templates)}\nIf a template fits perfectly, start your response with 'USE_TEMPLATE: [name]' followed by the filled template. Otherwise, generate a custom response."

        return f"""
Please generate a professional email response for the following email:

From: {sender}
Subject: {subject}

Email Content:
{email_content}

Additional Context:
{context}
{template_hint}

Requirements:
- Keep response concise (2-3 paragraphs max)
- Maintain professional tone
- Address the main points from the original email
- Include appropriate greeting and closing
- Do not include signature (will be added automatically)

Please also include the following analysis at the TOP of your response (hidden from user):
CATEGORY: [Inquiry / Support / Meeting / Feedback / Spam / Other]
SENTIMENT: [Positive / Neutral / Negative]
PRIORITY: [High / Medium / Low]
"""

    def _generate_fallback_response(self, subject: str) -> str:
        """Generate fallback response when AI fails"""
        return f"""Thank you for your email regarding "{subject}".

I have received your message and will review it carefully. I will get back to you with a detailed response as soon as possible.

Best regards"""


class TemplateManager:
    """Manages email templates loaded from templates.md."""

    def __init__(self, templates_path: str = "templates.md"):
        self.templates_path = templates_path
        self.templates = {}
        self.load_templates()

    def load_templates(self):
        """Parse templates from the markdown file."""
        if not os.path.exists(self.templates_path):
            return
        
        try:
            with open(self.templates_path, "r") as f:
                content = f.read()
                
            # Basic parsing: look for ### Header followed by ``` code blocks
            sections = re.split(r"### (.*)\n", content)
            for i in range(1, len(sections), 2):
                name = sections[i].strip().lower()
                body_match = re.search(r"```\n?(.*?)\n?```", sections[i+1], re.DOTALL)
                if body_match:
                    self.templates[name] = body_match.group(1).strip()
            
            logger.info(f"Loaded {len(self.templates)} email templates")
        except Exception as e:
            logger.error(f"Error loading templates: {e}")

    def get_template(self, name: str) -> Optional[str]:
        return self.templates.get(name.lower())

    def get_all_template_names(self) -> List[str]:
        return list(self.templates.keys())


class FilterManager:
    """Manages email filtering via blacklist and whitelist files."""

    def __init__(self, blacklist_path: str = "blacklist.txt", whitelist_path: str = "whitelist.txt"):
        self.blacklist_path = blacklist_path
        self.whitelist_path = whitelist_path
        self.blacklist = {"emails": set(), "domains": set(), "keywords": set(), "subjects": set()}
        self.whitelist = {"emails": set(), "domains": set()}
        self.load_filters()

    def load_filters(self):
        """Load filters from text files."""
        self._load_file(self.blacklist_path, self.blacklist)
        self._load_file(self.whitelist_path, self.whitelist)
        logger.info(f"Loaded {len(self.whitelist['emails'])} whitelisted emails, {len(self.blacklist['emails'])} blacklisted emails")

    def _load_file(self, path: str, target: Dict):
        if not os.path.exists(path):
            return
        try:
            with open(path, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if line.startswith("@"):
                        target["domains"].add(line[1:].lower())
                    elif line.startswith("*") and line.endswith("*"):
                        if "keywords" in target:
                            target["keywords"].add(line[1:-1].lower())
                    elif line.startswith("subject:"):
                        if "subjects" in target:
                            target["subjects"].add(line[8:].lower())
                    else:
                        target["emails"].add(line.lower())
        except Exception as e:
            logger.error(f"Error loading filter file {path}: {e}")

    def is_whitelisted(self, email_address: str) -> bool:
        """Check if an email is whitelisted."""
        email_lower = email_address.lower()
        if email_lower in self.whitelist["emails"]:
            return True
        domain = email_lower.split("@")[-1] if "@" in email_lower else ""
        return domain in self.whitelist["domains"]

    def is_blacklisted(self, email_address: str, subject: str) -> bool:
        """Check if an email or subject is blacklisted."""
        email_lower = email_address.lower()
        subject_lower = subject.lower()

        if email_lower in self.blacklist["emails"]:
            return True

        domain = email_lower.split("@")[-1] if "@" in email_lower else ""
        if domain in self.blacklist["domains"]:
            return True

        for kw in self.blacklist["keywords"]:
            if kw in email_lower:
                return True

        for skw in self.blacklist["subjects"]:
            if skw in subject_lower:
                return True

        return False


class EmailProcessor:
    """Main email processing class"""

    def __init__(
        self,
        config: EmailConfig,
        openrouter_api_key: str,
        signature: str = "",
        response_delay: int = 300,
    ):
        """
        Initialize the EmailProcessor.

        Args:
            config: Email configuration settings.
            openrouter_api_key: API key for OpenRouter.
            signature: Optional signature to append to responses.
            response_delay: Delay in seconds before sending a response. Defaults to 300.
        """
        self.config = config
        self.db = DatabaseManager()
        self.ai_client = OpenRouterClient(openrouter_api_key)
        self.signature = signature
        self.response_delay = response_delay
        self.processing_lock = Lock()
        self.is_running = False

        # Create attachments directory
        self.attachments_dir = "attachments"
        os.makedirs(self.attachments_dir, exist_ok=True)

        # Initialize filter manager
        self.filters = FilterManager()
        
        # Initialize template manager
        self.templates = TemplateManager()

        # Business hours (0=Monday, 6=Sunday)
        self.business_hours = {
            "start": 9,  # 9 AM
            "end": 18,   # 6 PM
            "days": [0, 1, 2, 3, 4]  # Mon-Fri
        }

    @retry_with_backoff(
        max_retries=3,
        initial_delay=2.0,
        exceptions=(imaplib.IMAP4.error, OSError, TimeoutError),
    )
    def connect_imap(self) -> imaplib.IMAP4_SSL:
        """Connect to IMAP server with retry logic"""
        try:
            if self.config.use_ssl:
                imap = imaplib.IMAP4_SSL(self.config.imap_server, self.config.imap_port)
            else:
                imap = imaplib.IMAP4(self.config.imap_server, self.config.imap_port)

            imap.login(self.config.email_address, self.config.password)
            logger.info("IMAP connection established successfully")
            return imap
        except imaplib.IMAP4.error as e:
            logger.error(f"IMAP authentication failed: {e}")
            raise
        except OSError as e:
            logger.error(f"IMAP network error: {e}")
            raise
        except Exception as e:
            logger.error(f"IMAP connection failed: {e}")
            raise

    @retry_with_backoff(
        max_retries=3,
        initial_delay=2.0,
        exceptions=(smtplib.SMTPException, OSError, TimeoutError),
    )
    def connect_smtp(self) -> smtplib.SMTP:
        """Connect to SMTP server with retry logic"""
        try:
            # For Gmail and most providers, use STARTTLS on port 587
            if self.config.smtp_port == 587:
                smtp = smtplib.SMTP(self.config.smtp_server, self.config.smtp_port, timeout=30)
                smtp.starttls()
            # For SSL/TLS on port 465
            elif self.config.smtp_port == 465:
                smtp = smtplib.SMTP_SSL(self.config.smtp_server, self.config.smtp_port, timeout=30)
            # For other configurations
            else:
                if self.config.use_ssl:
                    smtp = smtplib.SMTP_SSL(
                        self.config.smtp_server, self.config.smtp_port, timeout=30
                    )
                else:
                    smtp = smtplib.SMTP(self.config.smtp_server, self.config.smtp_port, timeout=30)
                    smtp.starttls()

            smtp.login(self.config.email_address, self.config.password)
            logger.info("SMTP connection established successfully")
            return smtp
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP authentication failed: {e}")
            raise
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error: {e}")
            raise
        except OSError as e:
            logger.error(f"SMTP network error: {e}")
            raise
        except Exception as e:
            logger.error(f"SMTP connection failed: {e}")
            raise

    def fetch_new_emails(self) -> List[EmailMessage]:
        """Fetch new emails from server"""
        try:
            imap = self.connect_imap()
            imap.select("INBOX")

            # Search for unread emails
            _, message_ids = imap.search(None, "UNSEEN")

            emails = []
            for msg_id in message_ids[0].split():
                try:
                    _, msg_data = imap.fetch(msg_id, "(RFC822)")
                    email_msg = email.message_from_bytes(msg_data[0][1])

                    parsed_email = self._parse_email(email_msg)
                    if parsed_email and self._should_process_email(parsed_email):
                        emails.append(parsed_email)

                except Exception as e:
                    logger.error(f"Error parsing email {msg_id}: {e}")
                    continue

            imap.close()
            imap.logout()

            return emails
        except Exception as e:
            logger.error(f"Error fetching emails: {e}")
            return []

    def _parse_email(self, email_msg) -> Optional[EmailMessage]:
        """
        Parse email message with validation and sanitization.

        Args:
            email_msg: The raw email message object.

        Returns:
            Optional[EmailMessage]: A parsed EmailMessage object, or None if invalid.
        """
        try:
            sender = self._get_sender(email_msg)
            if not sender:
                return None

            subject = self._get_subject(email_msg)
            msg_id = self._get_message_id(email_msg, sender)
            thread_id = self._get_thread_id(email_msg)

            # Extract body and attachments
            body, attachments = self._extract_content(email_msg)

            if not body or len(body.strip()) < 5:
                # If body is empty but there are attachments, still process
                if not attachments:
                    logger.warning(f"Email body too short or empty from {sender}")
                    return None
                body = "[This email contains only attachments]"

            timestamp = self._get_timestamp(email_msg)

            return EmailMessage(
                msg_id=msg_id,
                sender=sender,
                subject=subject,
                body=body,
                timestamp=timestamp,
                thread_id=thread_id,
                attachments=attachments,
            )

        except Exception as e:
            logger.error(f"Error parsing email: {e}")
            return None

    def _get_sender(self, email_msg) -> Optional[str]:
        """Extract and validate sender email address."""
        sender = email_msg.get("From", "")
        email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", sender)
        if email_match:
            sender_email = email_match.group(0)
            if not validate_email(sender_email):
                logger.warning(f"Invalid sender email format: {sender_email}")
                return None
            return sender
        logger.warning(f"Could not extract email address from: {sender}")
        return None

    def _get_subject(self, email_msg) -> str:
        """Extract and sanitize email subject."""
        subject = email_msg.get("Subject", "")
        if subject:
            try:
                decoded_header_list = decode_header(subject)
                subject_parts = []
                for content, encoding in decoded_header_list:
                    if encoding:
                        subject_parts.append(content.decode(encoding, errors="ignore"))
                    else:
                        if isinstance(content, bytes):
                            subject_parts.append(content.decode("utf-8", errors="ignore"))
                        else:
                            subject_parts.append(str(content))
                subject = "".join(subject_parts)
            except Exception as e:
                logger.warning(f"Error decoding subject: {e}")
                subject = "No Subject"

        return sanitize_text(subject, max_length=200)

    def _get_message_id(self, email_msg, sender: str) -> str:
        """Extract or generate a unique message ID."""
        msg_id = email_msg.get("Message-ID", "")
        if not msg_id:
            seed = sender.encode() + str(datetime.now()).encode()
            msg_id = f"<generated-{hashlib.md5(seed).hexdigest()}@mailmind>"
        return msg_id

    def _get_thread_id(self, email_msg) -> Optional[str]:
        """Extract thread ID from email headers."""
        references = email_msg.get("References", "").split()
        return email_msg.get("In-Reply-To") or (references[0] if references else None)


    def _get_timestamp(self, email_msg) -> datetime:
        """Extract and parse email timestamp."""
        timestamp = datetime.now()
        if email_msg.get("Date"):
            try:
                parsed_date = email.utils.parsedate_to_datetime(email_msg.get("Date"))
                if parsed_date.tzinfo is not None:
                    timestamp = parsed_date.replace(tzinfo=None)
                else:
                    timestamp = parsed_date
            except Exception as e:
                logger.warning(f"Error parsing date: {e}, using current time")
        return timestamp

    def _extract_content(self, email_msg) -> Tuple[str, List[Attachment]]:
        """
        Extract email body and attachments.

        Args:
            email_msg: The raw email message object.

        Returns:
            Tuple[str, List[Attachment]]: The plain text body and a list of Attachment objects.
        """
        body = ""
        attachments = []

        if email_msg.is_multipart():
            for part in email_msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))

                # Extract text body
                if content_type == "text/plain" and "attachment" not in content_disposition:
                    part_body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                    body += part_body
                elif content_type == "text/html" and not body and "attachment" not in content_disposition:
                    html_body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                    body = self._html_to_text(html_body)

                # Extract attachments
                elif "attachment" in content_disposition or part.get_filename():
                    attachment = self._save_attachment_file(part)
                    if attachment:
                        attachments.append(attachment)
        else:
            body = email_msg.get_payload(decode=True).decode("utf-8", errors="ignore")

        return body.strip(), attachments

    def _save_attachment_file(self, part) -> Optional[Attachment]:
        """Save an attachment part to disk and return metadata."""
        filename = part.get_filename()
        if not filename:
            return None

        # Sanitize filename
        filename = re.sub(r"[^\w\.-]", "_", filename[:100])

        # Generate unique path to avoid collisions
        unique_name = f"{int(time.time())}_{filename}"
        file_path = os.path.join(self.attachments_dir, unique_name)

        try:
            payload = part.get_payload(decode=True)
            with open(file_path, "wb") as f:
                f.write(payload)

            return Attachment(
                filename=filename,
                content_type=part.get_content_type(),
                size=len(payload),
                file_path=file_path,
            )
        except Exception as e:
            logger.error(f"Failed to save attachment {filename}: {e}")
            return None

    def _html_to_text(self, html: str) -> str:
        """Convert HTML to plain text"""
        # Remove HTML tags
        text = re.sub(r"<[^>]+>", " ", html)
        # Decode HTML entities
        text = unescape(text)
        # Clean up whitespace
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def _is_business_hours(self) -> bool:
        """Check if current time is within business hours."""
        now = datetime.now()
        if now.weekday() not in self.business_hours["days"]:
            return False
        return self.business_hours["start"] <= now.hour < self.business_hours["end"]

    def _should_process_email(self, email_msg: EmailMessage) -> bool:
        """Check if email should be processed based on filters and schedule."""
        # 1. Whitelist check (highest priority)
        if self.filters.is_whitelisted(email_msg.sender):
            logger.info(f"Whitelisted sender: {email_msg.sender}")
            return True

        # 2. Blacklist check
        if self.filters.is_blacklisted(email_msg.sender, email_msg.subject):
            logger.info(f"Blacklisted sender/subject: {email_msg.sender}")
            return False

        # 3. Business hours check
        if not self._is_business_hours():
            logger.info("Outside business hours. Skipping for now.")
            return False

        # 4. Basic checks from previous implementation (now integrated into FilterManager mostly, but keep age check)
        # Skip if too old (older than 24 hours)
        current_time = datetime.now()
        email_time = email_msg.timestamp
        if email_time.tzinfo is not None:
            email_time = email_time.replace(tzinfo=None)

        if current_time - email_time > timedelta(hours=24):
            logger.info(f"Skipping old email: {email_msg.subject}")
            return False

        return True

    def generate_and_send_response(self, email_msg: EmailMessage):
        """
        Generate an AI-powered response and send it via SMTP.

        Args:
            email_msg: The EmailMessage object to respond to.
        """
        try:
            # Generate AI response
            logger.info(f"Generating response for: {email_msg.subject}")

            # A/B Testing Logic (Performance/Enhancements)
            ab_version = random.choice(["A", "B"])
            context_prefix = ""
            if ab_version == "B":
                context_prefix = "[AB_VERSION_B: Be slightly more friendly than usual] "

            context = f"{context_prefix}This is a response to an email from {email_msg.sender}"
            
            # Threading context
            if email_msg.thread_id:
                history = self.db.get_thread_history(email_msg.thread_id)
                if history:
                    context += "\n\nPrevious conversation history:\n"
                    for h_msg in history[-5:]:
                        role = "User" if h_msg.sender != self.config.email_address else "Assistant"
                        context += f"{role}: {h_msg.body[:500]}...\n"

            # Attachments context
            if email_msg.attachments:
                att_list = ", ".join([a.filename for a in email_msg.attachments])
                context += f"\nThis email includes the following attachments: {att_list}. Please acknowledge them if appropriate."

            # Get available templates
            template_names = self.templates.get_all_template_names()

            ai_response, tokens_used, template_used, analysis = self.ai_client.generate_response(
                email_msg.body, 
                email_msg.sender, 
                email_msg.subject, 
                context,
                available_templates=template_names
            )

            # Update email message with analysis
            email_msg.category = analysis["category"]
            email_msg.sentiment = analysis["sentiment"]
            email_msg.priority = analysis["priority"]

            # If priority is High, log it specially (Priority Inbox)
            if email_msg.priority == "High":
                logger.warning(f"HIGH PRIORITY EMAIL detected from {email_msg.sender}")
                # Voice notification (System beep / CLI notification)
                print("\a") # ASCII Bell character (system beep)
                if os.name == "posix": # Mac/Linux voice notification
                    os.system('say "High priority email received" &')

            # If template was used
            if template_used:
                logger.info(f"AI used template: {template_used}")
                ai_response = ai_response.replace(f"USE_TEMPLATE: {template_used}", "").strip()

            # Add signature
            if self.signature and self.signature not in ai_response:
                ai_response = f"{ai_response}\n\n{self.signature}"

            # Wait for response delay
            if self.response_delay > 0:
                time.sleep(self.response_delay)

            # Send response
            self._send_response(email_msg, ai_response)

            # Save response and analysis
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                email_db_id = email_msg.id or self.db.save_email(email_msg)
                
                cursor.execute(
                    """
                    INSERT INTO responses (email_id, response_text, sent_at, model_used, tokens_used, ab_version)
                    VALUES (?, ?, ?, ?, ?, ?)
                """,
                    (
                        email_db_id,
                        ai_response,
                        datetime.now().isoformat(),
                        self.ai_client.model,
                        tokens_used,
                        ab_version
                    ),
                )
                conn.commit()

            # Mark as replied
            self.db.mark_as_replied(email_msg.msg_id)
            logger.info(f"Response sent successfully to: {email_msg.sender} (Category: {email_msg.category})")

        except Exception as e:
            logger.error(f"Error in generate_and_send_response: {e}")

    def report_metrics(self):
        """Generate a terminal-based metrics dashboard."""
        logger.info("--- MailMind Metrics Dashboard ---")
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Total stats
            cursor.execute("SELECT COUNT(*) FROM emails")
            total_emails = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM emails WHERE is_replied = 1")
            total_replied = cursor.fetchone()[0]
            
            # Category breakdown
            cursor.execute("SELECT category, COUNT(*) FROM emails GROUP BY category")
            categories = cursor.fetchall()
            
            # Sentiment breakdown
            cursor.execute("SELECT sentiment, COUNT(*) FROM emails GROUP BY sentiment")
            sentiments = cursor.fetchall()
            
            # API usage
            cursor.execute("SELECT SUM(tokens_used) FROM responses")
            total_tokens = cursor.fetchone()[0] or 0

            logger.info(f"Total Emails: {total_emails} | Replied: {total_replied}")
            logger.info(f"API Tokens Used: {total_tokens}")
            logger.info("Categories: " + ", ".join([f"{c[0]}: {c[1]}" for c in categories]))
            logger.info("Sentiments: " + ", ".join([f"{s[0]}: {s[1]}" for s in sentiments]))
        logger.info("----------------------------------")

    def _send_response(self, original_email: EmailMessage, response_text: str):
        """
        Prepare and send the SMTP response.

        Args:
            original_email: The original EmailMessage object.
            response_text: The generated text for the response.
        """
        try:
            smtp = self.connect_smtp()

            # Create response email
            msg = MIMEMultipart()
            msg["From"] = self.config.email_address
            msg["To"] = original_email.sender
            msg["Subject"] = f"Re: {original_email.subject}"

            # Add threading headers
            if original_email.thread_id:
                msg["In-Reply-To"] = original_email.msg_id
                msg["References"] = f"{original_email.thread_id} {original_email.msg_id}"
            else:
                msg["In-Reply-To"] = original_email.msg_id
                msg["References"] = original_email.msg_id

            # Add body
            msg.attach(MIMEText(response_text, "plain"))

            # Send email
            smtp.send_message(msg)
            smtp.quit()

        except Exception as e:
            logger.error(f"Error sending response: {e}")
            raise

    def process_emails(self):
        """Main email processing loop"""
        with self.processing_lock:
            try:
                # Fetch new emails
                new_emails = self.fetch_new_emails()

                # Save to database
                for email_msg in new_emails:
                    self.db.save_email(email_msg)

                # Process unreplied emails
                unreplied_emails = self.db.get_unreplied_emails()

                for email_msg in unreplied_emails:
                    # Add delay to avoid appearing too robotic
                    time.sleep(self.response_delay)

                    # Generate and send response
                    self.generate_and_send_response(email_msg)

                logger.info(f"Processed {len(unreplied_emails)} emails")

            except Exception as e:
                logger.error(f"Error in email processing: {e}")

    def start_monitoring(self, check_interval: int = 300):
        """Start email monitoring loop"""
        self.is_running = True
        logger.info("Starting MailMind email monitoring...")

        while self.is_running:
            try:
                self.process_emails()
                time.sleep(check_interval)
            except KeyboardInterrupt:
                logger.info("Stopping MailMind...")
                self.is_running = False
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(60)  # Wait before retrying

    def stop_monitoring(self):
        """Stop the email monitoring loop safely."""
        self.is_running = False


def validate_config_values(config: Dict) -> bool:
    """
    Validate configuration values for correct types and formats.

    Args:
        config: The configuration dictionary to validate.

    Returns:
        bool: True if valid, False otherwise.
    """
    try:
        # Email validation
        email_cfg = config.get("email", {})
        if not validate_email(email_cfg.get("email_address", "")):
            logger.error("Invalid EMAIL_ADDRESS in configuration")
            return False

        if not email_cfg.get("password"):
            logger.error("Missing EMAIL_PASSWORD in configuration")
            return False

        # Port validation
        ports = [
            ("IMAP_PORT", email_cfg.get("imap_port")),
            ("SMTP_PORT", email_cfg.get("smtp_port")),
        ]
        for name, port in ports:
            if not isinstance(port, int) or not (1 <= port <= 65535):
                logger.error(f"Invalid {name}: must be an integer between 1 and 65535")
                return False

        # OpenRouter validation
        or_cfg = config.get("openrouter", {})
        if not or_cfg.get("api_key"):
            logger.error("Missing OPENROUTER_API_KEY in configuration")
            return False

        # Interval validation
        settings = config.get("settings", {})
        intervals = [
            ("RESPONSE_DELAY", settings.get("response_delay")),
            ("CHECK_INTERVAL", settings.get("check_interval")),
        ]
        for name, val in intervals:
            if not isinstance(val, int) or val < 0:
                logger.error(f"Invalid {name}: must be a non-negative integer")
                return False

        return True
    except Exception as e:
        logger.error(f"Error during configuration validation: {e}")
        return False


def load_config(config_path: str = "config.json") -> Dict:
    """
    Load configuration from environment variables and JSON file.

    Args:
        config_path: Path to the JSON configuration file. Defaults to "config.json".

    Returns:
        Dict: A dictionary containing the loaded and validated configuration.
    """
    # Load environment variables from .env file
    load_dotenv()

    # Check for required environment variables
    required_env_vars = ["EMAIL_ADDRESS", "EMAIL_PASSWORD", "OPENROUTER_API_KEY"]

    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        logger.error("Please create a .env file with your credentials (see .env.example)")
        return {}

    # Load base configuration from JSON (for non-sensitive settings)
    base_config = {}
    try:
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                base_config = json.load(f)
        else:
            logger.warning(f"Config file {config_path} not found, using defaults")
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in config file: {e}")
        return {}

    # Build configuration with environment variables taking precedence
    try:
        config = {
            "email": {
                "imap_server": os.getenv(
                    "IMAP_SERVER",
                    base_config.get("email", {}).get("imap_server", "imap.gmail.com"),
                ),
                "imap_port": int(
                    os.getenv("IMAP_PORT", base_config.get("email", {}).get("imap_port", 993))
                ),
                "smtp_server": os.getenv(
                    "SMTP_SERVER",
                    base_config.get("email", {}).get("smtp_server", "smtp.gmail.com"),
                ),
                "smtp_port": int(
                    os.getenv("SMTP_PORT", base_config.get("email", {}).get("smtp_port", 587))
                ),
                "email_address": os.getenv("EMAIL_ADDRESS"),
                "password": os.getenv("EMAIL_PASSWORD"),
                "use_ssl": os.getenv("USE_SSL", "true").lower() == "true",
            },
            "openrouter": {
                "api_key": os.getenv("OPENROUTER_API_KEY"),
                "model": os.getenv(
                    "OPENROUTER_MODEL",
                    base_config.get("openrouter", {}).get("model", "mistralai/mistral-7b-instruct:free"),
                ),
            },
            "settings": {
                "signature": os.getenv(
                    "EMAIL_SIGNATURE", base_config.get("settings", {}).get("signature", "")
                ),
                "response_delay": int(
                    os.getenv(
                        "RESPONSE_DELAY",
                        base_config.get("settings", {}).get("response_delay", 300),
                    )
                ),
                "check_interval": int(
                    os.getenv(
                        "CHECK_INTERVAL",
                        base_config.get("settings", {}).get("check_interval", 300),
                    )
                ),
            },
        }

        # Validate values
        if not validate_config_values(config):
            return {}

        return config
    except ValueError as e:
        logger.error(f"Invalid configuration value (numeric field expected): {e}")
        return {}
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        return {}


def create_sample_config():
    """Create sample environment file"""
    env_template = """# MailMind Environment Configuration
# Copy this file to .env and fill in your actual values

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

# Database
DB_PATH=mailmind.db
"""

    if not os.path.exists(".env.example"):
        with open(".env.example", "w") as f:
            f.write(env_template)
        print("Sample configuration created: .env.example")

    if not os.path.exists(".env"):
        with open(".env", "w") as f:
            f.write(env_template)
        print("Environment file created: .env")

    print("\n" + "=" * 60)
    print("IMPORTANT: Please update .env with your actual credentials")
    print("=" * 60)
    print("\nRequired settings:")
    print("  - EMAIL_ADDRESS: Your email address")
    print("  - EMAIL_PASSWORD: Your app-specific password")
    print("  - OPENROUTER_API_KEY: Your OpenRouter API key")
    print("\nFor Gmail, generate an app password at:")
    print("  https://myaccount.google.com/apppasswords")


def main():
    """Main function"""
    # Check if .env file exists
    if not os.path.exists(".env"):
        logger.warning(".env file not found")
        create_sample_config()
        return

    # Load configuration
    config = load_config()
    if not config:
        logger.error("Failed to load configuration")
        return

    try:
        # Create email configuration
        email_config = EmailConfig(
            imap_server=config["email"]["imap_server"],
            imap_port=config["email"]["imap_port"],
            smtp_server=config["email"]["smtp_server"],
            smtp_port=config["email"]["smtp_port"],
            email_address=config["email"]["email_address"],
            password=config["email"]["password"],
            use_ssl=config["email"]["use_ssl"],
        )

        # Create email processor
        processor = EmailProcessor(
            config=email_config,
            openrouter_api_key=config["openrouter"]["api_key"],
            signature=config["settings"].get("signature", ""),
            response_delay=config["settings"].get("response_delay", 300),
        )

        # Start monitoring
        check_interval = config["settings"].get("check_interval", 300)
        processor.start_monitoring(check_interval)

    except KeyError as e:
        logger.error(f"Missing configuration key: {e}")
    except Exception as e:
        logger.error(f"Error starting MailMind: {e}")


if __name__ == "__main__":
    main()
