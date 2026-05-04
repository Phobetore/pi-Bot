"""Tests for the State container."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from pi_bot.colors import CANONICAL_COLORS, DEFAULT_COLOR
from pi_bot.state import State, is_valid_prefix


class TestPrefixValidation:
    @pytest.mark.parametrize("prefix", ["!", "?", "..", "!?", "$$$$$"])
    def test_valid(self, prefix: str) -> None:
        assert is_valid_prefix(prefix)

    @pytest.mark.parametrize(
        "prefix",
        ["", "abc", "123", "  ", "!!!!!!", "a", "1", "!a", " "],
    )
    def test_invalid(self, prefix: str) -> None:
        assert not is_valid_prefix(prefix)


class TestUserColor:
    async def test_default_color(self, state: State) -> None:
        assert state.get_user_color_name(123) == DEFAULT_COLOR

    async def test_set_canonical(self, state: State) -> None:
        canonical = await state.set_user_color(123, "red")
        assert canonical == "red"
        assert state.get_user_color_name(123) == "red"

    async def test_set_alias_resolves_to_canonical(self, state: State) -> None:
        canonical = await state.set_user_color(123, "rouge")
        assert canonical == "red"
        assert state.get_user_color_name(123) == "red"

    async def test_unknown_color_raises(self, state: State) -> None:
        with pytest.raises(ValueError):
            await state.set_user_color(123, "magentaviolet")

    async def test_color_marks_dirty(self, state: State) -> None:
        assert not state.is_dirty
        await state.set_user_color(1, "red")
        assert state.is_dirty


class TestServerPreferences:
    async def test_default_prefix(self, state: State) -> None:
        assert state.get_server_prefix(42, "!") == "!"

    async def test_set_and_get_prefix(self, state: State) -> None:
        await state.set_server_prefix(42, "?")
        assert state.get_server_prefix(42, "!") == "?"

    async def test_invalid_prefix_raises(self, state: State) -> None:
        with pytest.raises(ValueError):
            await state.set_server_prefix(42, "abc")

    async def test_default_language(self, state: State) -> None:
        assert state.get_server_language(42) == "en"

    async def test_set_language(self, state: State) -> None:
        await state.set_server_language(42, "fr")
        assert state.get_server_language(42) == "fr"

    async def test_invalid_language_raises(self, state: State) -> None:
        with pytest.raises(ValueError):
            await state.set_server_language(42, "zz")

    async def test_default_roll_default_none(self, state: State) -> None:
        assert state.get_server_default_roll(42) is None

    async def test_set_default_roll(self, state: State) -> None:
        await state.set_server_default_roll(42, "1d20")
        assert state.get_server_default_roll(42) == "1d20"

    async def test_language_in_dm_returns_english(self, state: State) -> None:
        assert state.get_server_language(None) == "en"


class TestPersistence:
    async def test_save_and_reload(self, tmp_path: Path) -> None:
        s1 = State(tmp_path)
        s1.load()
        await s1.set_user_color(1, "red")
        await s1.set_server_prefix(42, "?")
        await s1.set_server_language(42, "fr")
        await s1.set_server_default_roll(42, "1d20+5")
        await s1.increment_dice_rolls(1)
        await s1.save()

        s2 = State(tmp_path)
        s2.load()
        assert s2.get_user_color_name(1) == "red"
        assert s2.get_server_prefix(42, "!") == "?"
        assert s2.get_server_language(42) == "fr"
        assert s2.get_server_default_roll(42) == "1d20+5"
        assert s2.get_user_dice_count(1) == 1

    async def test_dirty_flag_cleared_after_save(self, state: State) -> None:
        await state.set_user_color(1, "red")
        assert state.is_dirty
        await state.save()
        assert not state.is_dirty

    async def test_legacy_french_color_migrated(self, tmp_path: Path) -> None:
        users_path = tmp_path / "user_preferences.json"
        users_path.write_text(
            json.dumps({"colors": {"bleu": "0x3498db"}, "users": {"1": {"color": "bleu"}}}),
            encoding="utf-8",
        )
        state = State(tmp_path)
        state.load()
        assert state.get_user_color_name(1) == "blue"
        # Migration should have set the dirty flag.
        assert state.is_dirty

    async def test_corrupted_state_starts_fresh(self, tmp_path: Path) -> None:
        servers_path = tmp_path / "server_preferences.json"
        servers_path.write_text("{not json", encoding="utf-8")
        state = State(tmp_path)
        state.load()
        # Did not crash, defaults used.
        assert state.get_server_language(123) == "en"


class TestSchemaSanitization:
    """Loaded JSON may have valid syntax but unexpected shape; we must not crash."""

    async def test_user_stats_with_string_value_is_dropped(
        self, tmp_path: Path
    ) -> None:
        (tmp_path / "user_stats.json").write_text(
            json.dumps({"123": "this should be a dict"}), encoding="utf-8"
        )
        state = State(tmp_path)
        state.load()
        assert state.get_user_dice_count(123) == 0
        # Subsequent mutations must succeed instead of crashing.
        await state.increment_dice_rolls(123)
        assert state.get_user_dice_count(123) == 1

    async def test_user_prefs_with_list_value_is_dropped(
        self, tmp_path: Path
    ) -> None:
        (tmp_path / "user_preferences.json").write_text(
            json.dumps({"users": {"42": [1, 2, 3]}}), encoding="utf-8"
        )
        state = State(tmp_path)
        state.load()
        assert state.get_user_color_name(42) == "blue"  # default
        await state.set_user_color(42, "red")  # must not crash
        assert state.get_user_color_name(42) == "red"

    async def test_server_prefs_with_wrong_type_field_is_filtered(
        self, tmp_path: Path
    ) -> None:
        (tmp_path / "server_preferences.json").write_text(
            json.dumps({"42": {"prefix": 123, "language": "fr"}}),
            encoding="utf-8",
        )
        state = State(tmp_path)
        state.load()
        # Wrong-type prefix is dropped; language survives.
        assert state.get_server_prefix(42, "!") == "!"
        assert state.get_server_language(42) == "fr"

    async def test_top_level_users_not_dict(self, tmp_path: Path) -> None:
        (tmp_path / "user_preferences.json").write_text(
            json.dumps({"users": "broken"}), encoding="utf-8"
        )
        state = State(tmp_path)
        state.load()
        assert state.get_user_color_name(1) == "blue"

    async def test_negative_count_reset_to_zero(self, tmp_path: Path) -> None:
        (tmp_path / "user_stats.json").write_text(
            json.dumps({"7": {"dice_rolls_count": -5}}), encoding="utf-8"
        )
        state = State(tmp_path)
        state.load()
        assert state.get_user_dice_count(7) == 0

    async def test_bool_count_reset_to_zero(self, tmp_path: Path) -> None:
        # bool is a subclass of int; we don't want True silently becoming 1.
        (tmp_path / "user_stats.json").write_text(
            json.dumps({"7": {"dice_rolls_count": True}}), encoding="utf-8"
        )
        state = State(tmp_path)
        state.load()
        assert state.get_user_dice_count(7) == 0

    async def test_sanitization_marks_dirty_so_repair_persists(
        self, tmp_path: Path
    ) -> None:
        (tmp_path / "user_stats.json").write_text(
            json.dumps({"123": "garbage"}), encoding="utf-8"
        )
        state = State(tmp_path)
        state.load()
        assert state.is_dirty
        await state.save()
        with (tmp_path / "user_stats.json").open(encoding="utf-8") as f:
            on_disk = json.load(f)
        # Either dropped entirely, or normalized to the canonical empty entry.
        assert "123" not in on_disk or on_disk["123"] == {"dice_rolls_count": 0}


class TestStats:
    async def test_increment(self, state: State) -> None:
        await state.increment_dice_rolls(7)
        await state.increment_dice_rolls(7)
        assert state.get_user_dice_count(7) == 2

    async def test_zero_for_unknown(self, state: State) -> None:
        assert state.get_user_dice_count(999) == 0


class TestColorIntegrity:
    async def test_all_canonical_resolvable(self, state: State) -> None:
        for canonical in CANONICAL_COLORS:
            await state.set_user_color(1, canonical)
            assert state.get_user_color_name(1) == canonical


class TestUserCompactPreference:
    async def test_default_is_false(self, state: State) -> None:
        assert state.get_user_compact(123) is False

    async def test_set_and_get_true(self, state: State) -> None:
        await state.set_user_compact(123, True)
        assert state.get_user_compact(123) is True

    async def test_set_back_to_false(self, state: State) -> None:
        await state.set_user_compact(123, True)
        await state.set_user_compact(123, False)
        assert state.get_user_compact(123) is False

    async def test_marks_dirty(self, state: State) -> None:
        await state.set_user_compact(123, True)
        assert state.is_dirty

    async def test_persists_across_reload(self, tmp_path) -> None:
        s1 = State(tmp_path)
        s1.load()
        await s1.set_user_compact(7, True)
        await s1.save()
        s2 = State(tmp_path)
        s2.load()
        assert s2.get_user_compact(7) is True

    async def test_color_and_compact_coexist(self, state: State) -> None:
        await state.set_user_color(7, "red")
        await state.set_user_compact(7, True)
        assert state.get_user_color_name(7) == "red"
        assert state.get_user_compact(7) is True

    async def test_corrupted_compact_value_dropped(self, tmp_path) -> None:
        import json as _json

        (tmp_path / "user_preferences.json").write_text(
            _json.dumps({"users": {"7": {"color": "red", "compact": "yes"}}}),
            encoding="utf-8",
        )
        state = State(tmp_path)
        state.load()
        # color survives, compact (wrong type) is dropped → default False.
        assert state.get_user_color_name(7) == "red"
        assert state.get_user_compact(7) is False
        assert state.is_dirty
