import pytest
import os
from scripts.template_loader import TemplateLoader


def test_template_loader_loads_file(tmp_path):
    template_file = tmp_path / "test_template.md"
    template_file.write_text("안녕 {{name}}!")
    loader = TemplateLoader(str(tmp_path))
    result = loader.load("test_template.md")
    assert result == "안녕 {{name}}!"


def test_template_loader_fills_placeholders(tmp_path):
    template_file = tmp_path / "template.md"
    template_file.write_text("{{greeting}} {{name}}!")
    loader = TemplateLoader(str(tmp_path))
    result = loader.render("template.md", {"greeting": "안녕", "name": "세계"})
    assert result == "안녕 세계!"


def test_template_loader_raises_on_missing_file(tmp_path):
    loader = TemplateLoader(str(tmp_path))
    with pytest.raises(FileNotFoundError):
        loader.load("nonexistent.md")


def test_template_loader_leaves_unfilled_placeholder_intact(tmp_path):
    template_file = tmp_path / "template.md"
    template_file.write_text("{{filled}} and {{unfilled}}")
    loader = TemplateLoader(str(tmp_path))
    result = loader.render("template.md", {"filled": "값"})
    assert "값" in result
    assert "{{unfilled}}" in result
