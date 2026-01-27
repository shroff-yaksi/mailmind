"""
Unit tests for database operations
"""

import pytest
import os
import tempfile
from datetime import datetime
from mailmind import DatabaseManager, EmailMessage


class TestDatabase:
    """Test database operations"""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing"""
        # Create a temporary file
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)

        # Create database manager
        db = DatabaseManager(db_path=path)

        yield db

        # Cleanup
        if os.path.exists(path):
            os.remove(path)

    def test_database_initialization(self, temp_db):
        """Test that database tables are created"""
        with temp_db.get_connection() as conn:
            cursor = conn.cursor()

            # Check emails table exists
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='emails'"
            )
            assert cursor.fetchone() is not None

            # Check responses table exists
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='responses'"
            )
            assert cursor.fetchone() is not None

    def test_save_email(self, temp_db, sample_email_message):
        """Test saving an email to database"""
        email_id = temp_db.save_email(sample_email_message)
        assert email_id is not None
        assert email_id > 0

    def test_mark_as_replied(self, temp_db, sample_email_message):
        """Test marking an email as replied"""
        # Save email
        temp_db.save_email(sample_email_message)

        # Mark as replied
        temp_db.mark_as_replied(sample_email_message.msg_id)

        # Verify it's marked as replied
        unreplied = temp_db.get_unreplied_emails()
        assert len(unreplied) == 0

    def test_get_unreplied_emails(self, temp_db):
        """Test retrieving unreplied emails"""
        # Create multiple emails
        email1 = EmailMessage(
            msg_id="<test1@example.com>",
            sender="sender1@example.com",
            subject="Test 1",
            body="Body 1",
            timestamp=datetime.now(),
            is_replied=False,
        )

        email2 = EmailMessage(
            msg_id="<test2@example.com>",
            sender="sender2@example.com",
            subject="Test 2",
            body="Body 2",
            timestamp=datetime.now(),
            is_replied=False,
        )

        # Save both
        temp_db.save_email(email1)
        temp_db.save_email(email2)

        # Mark one as replied
        temp_db.mark_as_replied(email1.msg_id)

        # Get unreplied
        unreplied = temp_db.get_unreplied_emails()
        assert len(unreplied) == 1
        assert unreplied[0].msg_id == email2.msg_id
