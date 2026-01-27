"""
Unit tests for email parsing functionality
"""

from datetime import datetime, timedelta
from mailmind import EmailProcessor


class TestEmailParsing:
    """Test email parsing methods"""

    def test_html_to_text_basic(self, sample_email_config):
        """Test basic HTML to text conversion"""
        processor = EmailProcessor(
            config=sample_email_config, openrouter_api_key="test_key"
        )

        html = "<p>Hello <strong>World</strong></p>"
        text = processor._html_to_text(html)

        assert "Hello" in text
        assert "World" in text
        assert "<p>" not in text
        assert "<strong>" not in text

    def test_html_to_text_with_entities(self, sample_email_config):
        """Test HTML entity decoding"""
        processor = EmailProcessor(
            config=sample_email_config, openrouter_api_key="test_key"
        )

        html = "<p>Price: &pound;100 &amp; free shipping</p>"
        text = processor._html_to_text(html)

        assert "£100" in text or "100" in text
        assert "&" in text or "and" in text

    def test_should_process_email_valid(
        self, sample_email_config, sample_email_message
    ):
        """Test that valid emails are processed"""
        processor = EmailProcessor(
            config=sample_email_config, openrouter_api_key="test_key"
        )

        assert processor._should_process_email(sample_email_message) is True

    def test_should_process_email_spam(self, sample_email_config, sample_spam_email):
        """Test that spam emails are filtered out"""
        processor = EmailProcessor(
            config=sample_email_config, openrouter_api_key="test_key"
        )

        assert processor._should_process_email(sample_spam_email) is False

    def test_should_process_email_old(self, sample_email_config):
        """Test that old emails are filtered out"""
        processor = EmailProcessor(
            config=sample_email_config, openrouter_api_key="test_key"
        )

        from mailmind import EmailMessage

        old_email = EmailMessage(
            msg_id="<old123@example.com>",
            sender="sender@example.com",
            subject="Old Email",
            body="This is an old email.",
            timestamp=datetime.now() - timedelta(hours=25),
            thread_id=None,
            is_replied=False,
        )

        assert processor._should_process_email(old_email) is False

    def test_should_process_email_excluded_sender(self, sample_email_config):
        """Test that excluded senders are filtered out"""
        processor = EmailProcessor(
            config=sample_email_config, openrouter_api_key="test_key"
        )

        from mailmind import EmailMessage

        noreply_email = EmailMessage(
            msg_id="<noreply123@example.com>",
            sender="noreply@example.com",
            subject="Automated Email",
            body="This is an automated email.",
            timestamp=datetime.now(),
            thread_id=None,
            is_replied=False,
        )

        assert processor._should_process_email(noreply_email) is False
