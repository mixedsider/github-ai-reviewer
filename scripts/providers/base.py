from abc import ABC, abstractmethod


class BaseProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def review(self, system_prompt: str, user_content: str) -> str: ...

    def review_with_retry(self, system_prompt: str, user_content: str) -> str:
        try:
            return self.review(system_prompt, user_content)
        except Exception:
            return self.review(system_prompt, user_content)
