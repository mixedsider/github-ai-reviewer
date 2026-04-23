import pytest
from scripts.providers.base import BaseProvider


def test_base_provider_cannot_be_instantiated_directly():
    with pytest.raises(TypeError):
        BaseProvider()


def test_base_provider_has_review_method():
    assert hasattr(BaseProvider, "review")


def test_base_provider_has_name_property():
    assert hasattr(BaseProvider, "name")
