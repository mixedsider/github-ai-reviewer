import openai
from .base import BaseProvider


class OpenAIProvider(BaseProvider):
    def __init__(self, api_key: str, model: str = "gpt-4o"):
        self._client = openai.OpenAI(api_key=api_key)
        self._model = model

    @property
    def name(self) -> str:
        return "openai"

    def review(self, system_prompt: str, user_content: str) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            max_tokens=4096,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
        )
        return response.choices[0].message.content
