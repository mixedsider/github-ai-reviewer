import pytest
from unittest.mock import MagicMock, patch
from scripts.providers.base import BaseProvider
from scripts.providers.anthropic_provider import AnthropicProvider


def test_base_provider_cannot_be_instantiated_directly():
    with pytest.raises(TypeError):
        BaseProvider()


def test_base_provider_has_review_method():
    assert hasattr(BaseProvider, "review")


def test_base_provider_has_name_property():
    assert hasattr(BaseProvider, "name")


def test_anthropic_provider_name():
    provider = AnthropicProvider(api_key="test-key")
    assert provider.name == "anthropic"


def test_anthropic_provider_review_calls_api():
    with patch("anthropic.Anthropic") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="리뷰 결과입니다.")]
        mock_client.messages.create.return_value = mock_response

        provider = AnthropicProvider(api_key="test-key")
        result = provider.review("시스템 프롬프트", "코드 내용")

        assert result == "리뷰 결과입니다."
        mock_client.messages.create.assert_called_once()


def test_anthropic_provider_uses_correct_model():
    with patch("anthropic.Anthropic") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="결과")]
        mock_client.messages.create.return_value = mock_response

        provider = AnthropicProvider(api_key="test-key", model="claude-opus-4-7")
        provider.review("prompt", "content")

        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs["model"] == "claude-opus-4-7"
