import pytest
from unittest.mock import MagicMock, patch
from scripts.providers.base import BaseProvider
from scripts.providers.anthropic_provider import AnthropicProvider
from scripts.providers.openai_provider import OpenAIProvider
from scripts.providers.local_provider import LocalProvider


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


def test_openai_provider_name():
    provider = OpenAIProvider(api_key="test-key")
    assert provider.name == "openai"


def test_openai_provider_review_calls_api():
    with patch("openai.OpenAI") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="GPT 리뷰 결과"))]
        mock_client.chat.completions.create.return_value = mock_response

        provider = OpenAIProvider(api_key="test-key")
        result = provider.review("시스템 프롬프트", "코드 내용")

        assert result == "GPT 리뷰 결과"


def test_openai_provider_default_model():
    with patch("openai.OpenAI"):
        provider = OpenAIProvider(api_key="test-key")
        assert provider._model == "gpt-4o"


def test_local_provider_name():
    provider = LocalProvider(base_url="http://localhost:11434", model_name="llama3")
    assert provider.name == "local"


def test_local_provider_review_calls_ollama_api():
    with patch("requests.post") as mock_post:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "로컬 모델 리뷰 결과"}}]
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        provider = LocalProvider(base_url="http://localhost:11434", model_name="llama3")
        result = provider.review("시스템 프롬프트", "코드 내용")

        assert result == "로컬 모델 리뷰 결과"
        mock_post.assert_called_once()


def test_local_provider_uses_openai_compatible_endpoint():
    with patch("requests.post") as mock_post:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "결과"}}]
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        provider = LocalProvider(base_url="http://localhost:11434", model_name="llama3")
        provider.review("prompt", "content")

        call_url = mock_post.call_args[0][0]
        assert "/v1/chat/completions" in call_url
