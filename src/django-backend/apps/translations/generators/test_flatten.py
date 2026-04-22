import pytest

from apps.translations.generators.flatten import flatten_en


def test_flatten_flat_dict_is_unchanged() -> None:
    assert flatten_en({"a": "1", "b": "2"}) == {"a": "1", "b": "2"}


def test_flatten_nested_dict_uses_dotted_keys() -> None:
    assert flatten_en({"nav": {"home": "Home", "profile": "Profile"}}) == {
        "nav.home": "Home",
        "nav.profile": "Profile",
    }


def test_flatten_deep_nesting() -> None:
    assert flatten_en({"a": {"b": {"c": "deep"}}}) == {"a.b.c": "deep"}


def test_flatten_rejects_non_string_leaves() -> None:
    with pytest.raises(TypeError, match="not a string"):
        flatten_en({"nav": {"home": 42}})
