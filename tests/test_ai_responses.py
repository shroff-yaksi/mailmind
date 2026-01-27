"""
Unit tests for AI response generation
"""
from unittest.mock import patch
from mailmind import OpenRouterClient


class TestAIResponseGeneration:
    """Test AI response generation functionality"""

    def test_openrouter_client_initialization(self):
        """Test OpenRouter client initialization"""
        client = OpenRouterClient(api_key="test_key", model="test_model")

        assert client.api_key == "test_key"
        assert client.model == "test_model"
        assert client.base_url == "https://openrouter.ai/api/v1"

    def test_build_prompt(self):
        """Test prompt building"""
        client = OpenRouterClient(api_key="test_key")

        prompt = client._build_prompt(
            email_content="Hello, I need help",
            sender="test@example.com",
            subject="Help Request",
            context="First time user",
        )

        assert "test@example.com" in prompt
        assert "Help Request" in prompt
        assert "Hello, I need help" in prompt
        assert "First time user" in prompt

    def test_fallback_response_generation(self):
        """Test fallback response generation"""
        client = OpenRouterClient(api_key="test_key")

        response = client._generate_fallback_response("Test Subject")

        assert "Test Subject" in response
        assert "Thank you" in response
        assert "received your message" in response

    @patch("mailmind.OpenRouterClient._make_api_request")
    def test_successful_response_generation(self, mock_request):
        """Test successful AI response generation"""
        mock_request.return_value = {
            "choices": [{"message": {"content": "This is an AI response"}}],
            "usage": {"total_tokens": 150},
        }

        client = OpenRouterClient(api_key="test_key")
        response, tokens = client.generate_response(
            email_content="Test email", sender="test@example.com", subject="Test"
        )

        assert response == "This is an AI response"
        assert tokens == 150

    @patch("mailmind.OpenRouterClient._make_api_request")
    def test_response_with_long_content(self, mock_request):
        """Test response generation with very long content"""
        mock_request.return_value = {
            "choices": [{"message": {"content": "Short response"}}],
            "usage": {"total_tokens": 100},
        }

        client = OpenRouterClient(api_key="test_key")
        long_content = "a" * 20000  # Very long content

        response, tokens = client.generate_response(
            email_content=long_content, sender="test@example.com", subject="Test"
        )

        # Should be sanitized to max length
        assert response == "Short response"
        assert tokens == 100

    @patch("mailmind.OpenRouterClient._make_api_request")
    def test_response_with_special_characters(self, mock_request):
        """Test response generation with special characters"""
        mock_request.return_value = {
            "choices": [{"message": {"content": "Response to special chars"}}],
            "usage": {"total_tokens": 50},
        }

        client = OpenRouterClient(api_key="test_key")

        response, tokens = client.generate_response(
            email_content="Test\x00with\nnull\tbytes",
            sender="test@example.com",
            subject="Special <chars>",
        )

        assert response == "Response to special chars"
        assert tokens == 50

    def test_api_request_timeout_handling(self):
        """Test API request timeout handling"""
        client = OpenRouterClient(api_key="test_key")

        with patch.object(client.session, "post") as mock_post:
            mock_post.side_effect = Exception("Timeout")

            # Should use fallback
            response, tokens = client.generate_response(
                email_content="Test", sender="test@example.com", subject="Test Subject"
            )

            assert "Thank you for your email" in response
            assert tokens == 0

    @patch("mailmind.OpenRouterClient._make_api_request")
    def test_missing_usage_data(self, mock_request):
        """Test handling of missing usage data in API response"""
        mock_request.return_value = {
            "choices": [{"message": {"content": "Response without usage"}}]
            # No usage field
        }

        client = OpenRouterClient(api_key="test_key")
        response, tokens = client.generate_response(
            email_content="Test", sender="test@example.com", subject="Test"
        )

        assert response == "Response without usage"
        assert tokens == 0  # Should default to 0

    @patch("mailmind.OpenRouterClient._make_api_request")
    def test_context_in_prompt(self, mock_request):
        """Test that context is properly included in prompt"""
        mock_request.return_value = {
            "choices": [{"message": {"content": "Contextual response"}}],
            "usage": {"total_tokens": 75},
        }

        client = OpenRouterClient(api_key="test_key")
        response, tokens = client.generate_response(
            email_content="Question about product",
            sender="customer@example.com",
            subject="Product Inquiry",
            context="Returning customer, previous purchase: Widget X",
        )

        assert response == "Contextual response"
        # Verify the prompt was called with context
        call_args = mock_request.call_args
        assert call_args is not None
