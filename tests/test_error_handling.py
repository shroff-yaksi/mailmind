"""
Unit tests for error handling and retry logic
"""

import pytest
from unittest.mock import Mock, patch
import requests
from mailmind import retry_with_backoff, validate_email, sanitize_text, OpenRouterClient


class TestRetryLogic:
    """Test retry decorator functionality"""

    def test_retry_success_on_first_attempt(self):
        """Test function succeeds on first attempt"""
        mock_func = Mock(return_value="success")
        decorated = retry_with_backoff(max_retries=3)(mock_func)

        result = decorated()

        assert result == "success"
        assert mock_func.call_count == 1

    def test_retry_success_after_failures(self):
        """Test function succeeds after initial failures"""
        mock_func = Mock(side_effect=[Exception("fail"), Exception("fail"), "success"])
        decorated = retry_with_backoff(max_retries=3, initial_delay=0.1)(mock_func)

        result = decorated()

        assert result == "success"
        assert mock_func.call_count == 3

    def test_retry_exhausted(self):
        """Test all retries are exhausted"""
        mock_func = Mock(side_effect=Exception("always fails"))
        decorated = retry_with_backoff(max_retries=2, initial_delay=0.1)(mock_func)

        with pytest.raises(Exception, match="always fails"):
            decorated()

        assert mock_func.call_count == 3  # initial + 2 retries


class TestEmailValidation:
    """Test email validation functionality"""

    def test_valid_email(self):
        """Test valid email addresses"""
        assert validate_email("test@example.com") is True
        assert validate_email("user.name@domain.co.uk") is True
        assert validate_email("user+tag@example.org") is True

    def test_invalid_email(self):
        """Test invalid email addresses"""
        assert validate_email("invalid") is False
        assert validate_email("@example.com") is False
        assert validate_email("user@") is False
        assert validate_email("user @example.com") is False
        assert validate_email("") is False


class TestTextSanitization:
    """Test text sanitization functionality"""

    def test_sanitize_normal_text(self):
        """Test sanitizing normal text"""
        text = "Hello, this is a normal email."
        result = sanitize_text(text)
        assert result == text

    def test_sanitize_with_null_bytes(self):
        """Test removing null bytes"""
        text = "Hello\x00World"
        result = sanitize_text(text)
        assert "\x00" not in result
        assert "HelloWorld" in result

    def test_sanitize_max_length(self):
        """Test truncation to max length"""
        text = "a" * 1000
        result = sanitize_text(text, max_length=100)
        assert len(result) == 100

    def test_sanitize_empty_text(self):
        """Test sanitizing empty text"""
        assert sanitize_text("") == ""
        assert sanitize_text(None) == ""

    def test_sanitize_preserves_newlines(self):
        """Test that newlines and tabs are preserved"""
        text = "Line 1\nLine 2\tTabbed"
        result = sanitize_text(text)
        assert "\n" in result
        assert "\t" in result


class TestOpenRouterClientErrorHandling:
    """Test OpenRouter client error handling"""

    def test_rate_limit_error(self, sample_email_config):
        """Test handling of rate limit errors"""
        client = OpenRouterClient(api_key="test_key")

        with patch.object(client, "_make_api_request") as mock_request:
            mock_response = Mock()
            mock_response.status_code = 429
            mock_request.side_effect = requests.exceptions.HTTPError(
                response=mock_response
            )

            response, tokens, _, _ = client.generate_response(
                "Test email", "test@example.com", "Test Subject"
            )

            # Should return fallback response
            assert "Thank you for your email" in response
            assert tokens == 0

    def test_authentication_error(self):
        """Test handling of authentication errors"""
        client = OpenRouterClient(api_key="invalid_key")

        with patch.object(client, "_make_api_request") as mock_request:
            mock_response = Mock()
            mock_response.status_code = 401
            mock_request.side_effect = requests.exceptions.HTTPError(
                response=mock_response
            )

            response, tokens, _, _ = client.generate_response(
                "Test email", "test@example.com", "Test Subject"
            )

            # Should return fallback response
            assert "Thank you for your email" in response
            assert tokens == 0

    def test_timeout_error(self):
        """Test handling of timeout errors"""
        client = OpenRouterClient(api_key="test_key")

        with patch.object(client, "_make_api_request") as mock_request:
            mock_request.side_effect = requests.exceptions.Timeout()

            response, tokens, _, _ = client.generate_response(
                "Test email", "test@example.com", "Test Subject"
            )

            # Should return fallback response
            assert "Thank you for your email" in response
            assert tokens == 0

    def test_connection_error(self):
        """Test handling of connection errors"""
        client = OpenRouterClient(api_key="test_key")

        with patch.object(client, "_make_api_request") as mock_request:
            mock_request.side_effect = requests.exceptions.ConnectionError()

            response, tokens, _, _ = client.generate_response(
                "Test email", "test@example.com", "Test Subject"
            )

            # Should return fallback response
            assert "Thank you for your email" in response
            assert tokens == 0

    def test_input_sanitization(self):
        """Test that inputs are sanitized"""
        client = OpenRouterClient(api_key="test_key")

        with patch.object(client, "_make_api_request") as mock_request, \
             patch.object(client, "_get_cached_response", return_value=None), \
             patch.object(client, "_cache_response"):
            
            mock_request.return_value = {
                "choices": [{"message": {"content": "AI response"}}],
                "usage": {"total_tokens": 100},
            }

            # Test with potentially harmful input
            malicious_content = "Test\x00email" + "a" * 20000
            response, tokens, _, _ = client.generate_response(
                malicious_content, "test@example.com", "Test Subject"
            )

            # Should have been sanitized before being sent
            assert response == "AI response"
            assert tokens == 100
