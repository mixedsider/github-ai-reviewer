import time
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class BaseProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def review(self, system_prompt: str, user_content: str) -> str: ...

    def review_with_retry(self, system_prompt: str, user_content: str) -> str:
        try:
            return self.review(system_prompt, user_content)
        except Exception as e:
            logger.warning("AI 리뷰 실패, 1초 후 재시도: %s", e)
            time.sleep(1)
            return self.review(system_prompt, user_content)
