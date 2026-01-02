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
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import requests
from threading import Thread, Lock
import sqlite3
from contextlib import contextmanager
import re
from html import unescape
import hashlib


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mailmind.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


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
class EmailMessage:
    """Email message data structure"""
    msg_id: str
    sender: str
    subject: str
    body: str
    timestamp: datetime
    thread_id: Optional[str] = None
    is_replied: bool = False


class DatabaseManager:
    """Database manager for storing email data and responses"""
    
    def __init__(self, db_path: str = "mailmind.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database tables"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Emails table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS emails (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    msg_id TEXT UNIQUE,
                    sender TEXT,
                    subject TEXT,
                    body TEXT,
                    timestamp TEXT,
                    thread_id TEXT,
                    is_replied BOOLEAN DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Responses table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS responses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email_id INTEGER,
                    response_text TEXT,
                    sent_at TEXT,
                    model_used TEXT,
                    tokens_used INTEGER,
                    FOREIGN KEY (email_id) REFERENCES emails (id)
                )
            ''')
            
            # Settings table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            ''')
            
            conn.commit()
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
        finally:
            conn.close()
    
    def save_email(self, email_msg: EmailMessage) -> int:
        """Save email to database"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO emails 
                (msg_id, sender, subject, body, timestamp, thread_id, is_replied)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                email_msg.msg_id,
                email_msg.sender,
                email_msg.subject,
                email_msg.body,
                email_msg.timestamp.isoformat(),
                email_msg.thread_id,
                email_msg.is_replied
            ))
            conn.commit()
            return cursor.lastrowid
    
    def mark_as_replied(self, msg_id: str):
        """Mark email as replied"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE emails SET is_replied = 1 WHERE msg_id = ?',
                (msg_id,)
            )
            conn.commit()
    
    def get_unreplied_emails(self) -> List[EmailMessage]:
        """Get unreplied emails from database"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT msg_id, sender, subject, body, timestamp, thread_id, is_replied
                FROM emails WHERE is_replied = 0
                ORDER BY timestamp ASC
            ''')
            
            emails = []
            for row in cursor.fetchall():
                emails.append(EmailMessage(
                    msg_id=row[0],
                    sender=row[1],
                    subject=row[2],
                    body=row[3],
                    timestamp=datetime.fromisoformat(row[4]),
                    thread_id=row[5],
                    is_replied=bool(row[6])
                ))
            return emails


class OpenRouterClient:
    """OpenRouter API client for AI responses"""
    
    def __init__(self, api_key: str, model: str = "anthropic/claude-3-sonnet"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://openrouter.ai/api/v1"
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        })
    
    def generate_response(self, email_content: str, sender: str, subject: str, 
                         context: str = "", max_tokens: int = 500) -> Tuple[str, int]:
        """Generate AI response for email"""
        try:
            prompt = self._build_prompt(email_content, sender, subject, context)
            
            response = self.session.post(
                f"{self.base_url}/chat/completions",
                json={
                    "model": self.model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a professional email assistant. Generate concise, helpful, and contextually appropriate email responses. Be polite, professional, and direct."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "max_tokens": max_tokens,
                    "temperature": 0.7
                },
                timeout=30
            )
            
            response.raise_for_status()
            data = response.json()
            
            ai_response = data["choices"][0]["message"]["content"]
            tokens_used = data.get("usage", {}).get("total_tokens", 0)
            
            return ai_response, tokens_used
            
        except requests.exceptions.RequestException as e:
            logger.error(f"OpenRouter API error: {e}")
            return self._generate_fallback_response(subject), 0
        except Exception as e:
            logger.error(f"Unexpected error in AI response generation: {e}")
            return self._generate_fallback_response(subject), 0
    
    def _build_prompt(self, email_content: str, sender: str, subject: str, context: str) -> str:
        """Build AI prompt for email response"""
        return f"""
Please generate a professional email response for the following email:

From: {sender}
Subject: {subject}

Email Content:
{email_content}

Additional Context:
{context}

Requirements:
- Keep response concise (2-3 paragraphs max)
- Maintain professional tone
- Address the main points from the original email
- Include appropriate greeting and closing
- Do not include signature (will be added automatically)
"""
    
    def _generate_fallback_response(self, subject: str) -> str:
        """Generate fallback response when AI fails"""
        return f"""Thank you for your email regarding "{subject}".

I have received your message and will review it carefully. I will get back to you with a detailed response as soon as possible.

Best regards"""


class EmailProcessor:
    """Main email processing class"""
    
    def __init__(self, config: EmailConfig, openrouter_api_key: str, 
                 signature: str = "", response_delay: int = 300):
        self.config = config
        self.db = DatabaseManager()
        self.ai_client = OpenRouterClient(openrouter_api_key)
        self.signature = signature
        self.response_delay = response_delay
        self.processing_lock = Lock()
        self.is_running = False
        
        # Email filters
        self.spam_keywords = [
            "viagra", "lottery", "winner", "congratulations", "urgent",
            "act now", "limited time", "free money", "nigerian prince"
        ]
        
        # Auto-reply exclusions
        self.exclude_senders = [
            "noreply", "no-reply", "donotreply", "automated", "newsletter"
        ]
    
    def connect_imap(self) -> imaplib.IMAP4_SSL:
        """Connect to IMAP server"""
        try:
            if self.config.use_ssl:
                imap = imaplib.IMAP4_SSL(self.config.imap_server, self.config.imap_port)
            else:
                imap = imaplib.IMAP4(self.config.imap_server, self.config.imap_port)
            
            imap.login(self.config.email_address, self.config.password)
            return imap
        except Exception as e:
            logger.error(f"IMAP connection failed: {e}")
            raise
    
    def connect_smtp(self) -> smtplib.SMTP:
        """Connect to SMTP server"""
        try:
            # For Gmail and most providers, use STARTTLS on port 587
            if self.config.smtp_port == 587:
                smtp = smtplib.SMTP(self.config.smtp_server, self.config.smtp_port)
                smtp.starttls()
            # For SSL/TLS on port 465
            elif self.config.smtp_port == 465:
                smtp = smtplib.SMTP_SSL(self.config.smtp_server, self.config.smtp_port)
            # For other configurations
            else:
                if self.config.use_ssl:
                    smtp = smtplib.SMTP_SSL(self.config.smtp_server, self.config.smtp_port)
                else:
                    smtp = smtplib.SMTP(self.config.smtp_server, self.config.smtp_port)
                    smtp.starttls()
            
            smtp.login(self.config.email_address, self.config.password)
            return smtp
        except Exception as e:
            logger.error(f"SMTP connection failed: {e}")
            raise
    
    def fetch_new_emails(self) -> List[EmailMessage]:
        """Fetch new emails from server"""
        try:
            imap = self.connect_imap()
            imap.select('INBOX')
            
            # Search for unread emails
            _, message_ids = imap.search(None, 'UNSEEN')
            
            emails = []
            for msg_id in message_ids[0].split():
                try:
                    _, msg_data = imap.fetch(msg_id, '(RFC822)')
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
        """Parse email message"""
        try:
            # Get sender
            sender = email_msg.get('From', '')
            
            # Get subject
            subject = email_msg.get('Subject', '')
            if subject:
                decoded_subject = decode_header(subject)[0]
                if decoded_subject[1]:
                    subject = decoded_subject[0].decode(decoded_subject[1])
                else:
                    subject = decoded_subject[0]
            
            # Get message ID
            msg_id = email_msg.get('Message-ID', '')
            
            # Get thread ID (In-Reply-To or References)
            thread_id = email_msg.get('In-Reply-To') or email_msg.get('References', '').split()[0] if email_msg.get('References') else None
            
            # Get email body
            body = self._extract_body(email_msg)
            
            # Get timestamp
            timestamp = datetime.now()
            if email_msg.get('Date'):
                try:
                    parsed_date = email.utils.parsedate_to_datetime(email_msg.get('Date'))
                    # Convert to naive datetime if timezone-aware
                    if parsed_date.tzinfo is not None:
                        timestamp = parsed_date.replace(tzinfo=None)
                    else:
                        timestamp = parsed_date
                except:
                    # Fall back to current time if parsing fails
                    timestamp = datetime.now()
            
            return EmailMessage(
                msg_id=msg_id,
                sender=sender,
                subject=subject,
                body=body,
                timestamp=timestamp,
                thread_id=thread_id
            )
            
        except Exception as e:
            logger.error(f"Error parsing email: {e}")
            return None
    
    def _extract_body(self, email_msg) -> str:
        """Extract email body text"""
        body = ""
        
        if email_msg.is_multipart():
            for part in email_msg.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                    break
                elif part.get_content_type() == "text/html" and not body:
                    html_body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                    body = self._html_to_text(html_body)
        else:
            body = email_msg.get_payload(decode=True).decode('utf-8', errors='ignore')
        
        return body.strip()
    
    def _html_to_text(self, html: str) -> str:
        """Convert HTML to plain text"""
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', ' ', html)
        # Decode HTML entities
        text = unescape(text)
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def _should_process_email(self, email_msg: EmailMessage) -> bool:
        """Check if email should be processed"""
        # Skip if already replied
        if email_msg.is_replied:
            return False
        
        # Skip excluded senders
        sender_lower = email_msg.sender.lower()
        if any(exclude in sender_lower for exclude in self.exclude_senders):
            logger.info(f"Skipping excluded sender: {email_msg.sender}")
            return False
        
        # Skip potential spam
        content_lower = (email_msg.subject + " " + email_msg.body).lower()
        if any(keyword in content_lower for keyword in self.spam_keywords):
            logger.info(f"Skipping potential spam: {email_msg.subject}")
            return False
        
        # Skip if too old (older than 24 hours)
        current_time = datetime.now()
        email_time = email_msg.timestamp
        
        # Ensure both datetimes are timezone-naive for comparison
        if email_time.tzinfo is not None:
            email_time = email_time.replace(tzinfo=None)
        
        if current_time - email_time > timedelta(hours=24):
            logger.info(f"Skipping old email: {email_msg.subject}")
            return False
        
        return True
    
    def generate_and_send_response(self, email_msg: EmailMessage):
        """Generate AI response and send email"""
        try:
            # Generate AI response
            logger.info(f"Generating response for: {email_msg.subject}")
            
            context = f"This is a response to an email from {email_msg.sender}"
            if email_msg.thread_id:
                context += " (part of an ongoing conversation)"
            
            ai_response, tokens_used = self.ai_client.generate_response(
                email_msg.body,
                email_msg.sender,
                email_msg.subject,
                context
            )
            
            # Add signature if provided
            full_response = ai_response
            if self.signature:
                full_response += f"\n\n{self.signature}"
            
            # Send response
            self._send_response(email_msg, full_response)
            
            # Mark as replied in database
            self.db.mark_as_replied(email_msg.msg_id)
            
            logger.info(f"Response sent successfully for: {email_msg.subject}")
            
        except Exception as e:
            logger.error(f"Error generating/sending response: {e}")
    
    def _send_response(self, original_email: EmailMessage, response_text: str):
        """Send email response"""
        try:
            smtp = self.connect_smtp()
            
            # Create response email
            msg = MIMEMultipart()
            msg['From'] = self.config.email_address
            msg['To'] = original_email.sender
            msg['Subject'] = f"Re: {original_email.subject}"
            
            # Add threading headers
            if original_email.thread_id:
                msg['In-Reply-To'] = original_email.msg_id
                msg['References'] = f"{original_email.thread_id} {original_email.msg_id}"
            else:
                msg['In-Reply-To'] = original_email.msg_id
                msg['References'] = original_email.msg_id
            
            # Add body
            msg.attach(MIMEText(response_text, 'plain'))
            
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
        """Stop email monitoring"""
        self.is_running = False


def load_config(config_path: str = "config.json") -> Dict:
    """Load configuration from JSON file"""
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"Config file {config_path} not found")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in config file: {e}")
        return {}


def create_sample_config():
    """Create sample configuration file"""
    config = {
        "email": {
            "imap_server": "imap.gmail.com",
            "imap_port": 993,
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "email_address": "your.email@gmail.com",
            "password": "your_app_password",
            "use_ssl": True
        },
        "openrouter": {
            "api_key": "your_openrouter_api_key",
            "model": "anthropic/claude-3-sonnet"
        },
        "settings": {
            "signature": "Best regards,\nYour Name\nYour Company",
            "response_delay": 300,
            "check_interval": 300
        }
    }
    
    with open("config.json", 'w') as f:
        json.dump(config, f, indent=2)
    
    print("Sample configuration created: config.json")
    print("Please update the configuration with your credentials.")


def main():
    """Main function"""
    # Check if config exists
    if not os.path.exists("config.json"):
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
            use_ssl=config["email"]["use_ssl"]
        )
        
        # Create email processor
        processor = EmailProcessor(
            config=email_config,
            openrouter_api_key=config["openrouter"]["api_key"],
            signature=config["settings"].get("signature", ""),
            response_delay=config["settings"].get("response_delay", 300)
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