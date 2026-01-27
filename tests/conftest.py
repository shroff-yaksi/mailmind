"""
Pytest configuration and shared fixtures for MailMind tests
"""

import pytest
from datetime import datetime
from mailmind import EmailMessage, EmailConfig


@pytest.fixture
def sample_email_config():
    """Sample email configuration for testing"""
    return EmailConfig(
        imap_server="imap.gmail.com",
        imap_port=993,
        smtp_server="smtp.gmail.com",
        smtp_port=587,
        email_address="test@example.com",
        password="test_password",
        use_ssl=True,
    )


@pytest.fixture
def sample_email_message():
    """Sample email message for testing"""
    return EmailMessage(
        msg_id="<test123@example.com>",
        sender="sender@example.com",
        subject="Test Subject",
        body="This is a test email body.",
        timestamp=datetime.now(),
        thread_id=None,
        is_replied=False,
    )


@pytest.fixture
def sample_spam_email():
    """Sample spam email for testing filters"""
    return EmailMessage(
        msg_id="<spam123@example.com>",
        sender="spammer@example.com",
        subject="URGENT: You won the lottery!!!",
        body="Congratulations! Click here to claim your prize. Act now!",
        timestamp=datetime.now(),
        thread_id=None,
        is_replied=False,
    )


@pytest.fixture
def sample_html_email():
    """Sample HTML email content"""
    return """
    <html>
        <body>
            <h1>Test Email</h1>
            <p>This is a <strong>test</strong> email with HTML content.</p>
            <a href="https://example.com">Click here</a>
        </body>
    </html>
    """
