import os


class TemplateLoader:
    def __init__(self, templates_dir: str):
        self._dir = templates_dir

    def load(self, filename: str) -> str:
        path = os.path.join(self._dir, filename)
        if not os.path.exists(path):
            raise FileNotFoundError(f"템플릿 파일을 찾을 수 없습니다: {path}")
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def render(self, filename: str, variables: dict) -> str:
        content = self.load(filename)
        for key, value in variables.items():
            content = content.replace(f"{{{{{key}}}}}", str(value))
        return content
