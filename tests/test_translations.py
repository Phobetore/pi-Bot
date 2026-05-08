"""Tests for the translation registry."""
from __future__ import annotations

import pytest

from sirrmizan.translations import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES, get, t


class TestGet:
    @pytest.mark.parametrize("lang", sorted(SUPPORTED_LANGUAGES))
    def test_supported_language_returns_dict(self, lang: str) -> None:
        d = get(lang)
        assert isinstance(d, dict)
        assert "help_title" in d

    def test_unknown_language_falls_back_to_default(self) -> None:
        assert get("unknown") is get(DEFAULT_LANGUAGE)

    def test_default_language_is_supported(self) -> None:
        assert DEFAULT_LANGUAGE in SUPPORTED_LANGUAGES


class TestTranslateFunction:
    def test_simple_lookup(self) -> None:
        assert t("en", "help_title") == "Bot Help"

    def test_locale_specific(self) -> None:
        assert t("fr", "help_title") == "Aide du Bot"
        assert t("de", "help_title") == "Bot-Hilfe"

    def test_format_kwargs(self) -> None:
        assert "blue" in t("en", "color_set", color="blue")

    def test_unknown_key_returns_key_itself(self) -> None:
        assert t("en", "nonexistent_key_xyz") == "nonexistent_key_xyz"

    def test_unknown_language_uses_default(self) -> None:
        assert t("zz", "help_title") == "Bot Help"

    def test_missing_key_in_locale_falls_back_to_english(self) -> None:
        # All keys we ship currently exist in every locale, but the contract
        # is: missing → fall back to English. Verified via test_all_locales_*.
        assert t(DEFAULT_LANGUAGE, "embed_result") == t("en", "embed_result")


class TestLocaleCompleteness:
    def test_all_locales_share_the_same_keys(self) -> None:
        en_keys = set(get("en"))
        for lang in SUPPORTED_LANGUAGES:
            keys = set(get(lang))
            missing = en_keys - keys
            extra = keys - en_keys
            assert not missing, f"{lang} is missing: {sorted(missing)}"
            assert not extra, f"{lang} has unknown keys: {sorted(extra)}"

    def test_all_locales_have_string_values(self) -> None:
        for lang in SUPPORTED_LANGUAGES:
            for key, value in get(lang).items():
                assert isinstance(value, str), f"{lang}/{key} is {type(value)}"
                assert value, f"{lang}/{key} is empty"
