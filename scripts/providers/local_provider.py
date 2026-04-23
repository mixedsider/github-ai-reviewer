import requests
from .base import BaseProvider


class LocalProvider(BaseProvider):
    def __init__(self, base_url: str, model_name: str):
        self._base_url = base_url.rstrip("/")
        self._model_name = model_name

    @property
    def name(self) -> str:
        return "local"

    def review(self, system_prompt: str, user_content: str) -> str:
        url = f"{self._base_url}/v1/chat/completions"
        payload = {
            "model": self._model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
        }
        response = requests.post(url, json=payload, timeout=120)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
