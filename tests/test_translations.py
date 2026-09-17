"""Guards against the class of UI bugs that only show up when HA renders text.

These bugs (unescaped literal braces breaking the frontend's placeholder
substitution, markdown syntax showing up as literal asterisks/backticks
because the frontend renders descriptions as plain text, translation files
drifting out of sync) were previously only caught by manually installing the
integration into a running Home Assistant, opening the config flow in the
browser, and looking at it. They don't need a browser: HA's own translation
loader can render the exact same flattened strings the frontend receives, and
static checks on the JSON catch the rest.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import translation

from custom_components.template_forecast.const import DOMAIN

COMPONENT_DIR = Path("custom_components/template_forecast")

# Placeholders the config flow actually substitutes into description strings
# (see config_flow.py: description_placeholders=...).
KNOWN_PLACEHOLDERS = {
    "source_entity",
    "attribute_template_error",
    "state_template_error",
}

# Markdown that HA's config flow frontend does NOT render - it shows these
# characters literally instead of formatting them. Regression guard for the
# "rewrite section descriptions as plain text, no markdown" fix.
_MARKDOWN_PATTERNS = [
    re.compile(r"\*\*[^*]+\*\*"),  # **bold**
    re.compile(r"`[^`]+`"),  # `code`
    re.compile(r"\[[^\]]+\]\([^)]+\)"),  # [text](link)
    re.compile(r"^#{1,6}\s", re.MULTILINE),  # # heading
    re.compile(r"^[-*]\s", re.MULTILINE),  # - bullet / * bullet
]


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _walk_strings(data: Any, path: str = "") -> list[tuple[str, str]]:
    """Flatten a strings/translations JSON tree to (path, value) for every leaf string."""
    results: list[tuple[str, str]] = []
    if isinstance(data, dict):
        for key, value in data.items():
            results.extend(_walk_strings(value, f"{path}.{key}" if path else key))
    elif isinstance(data, str):
        results.append((path, data))
    return results


def _icu_argument_names(text: str) -> list[str]:
    """Parse `text` as ICU MessageFormat and return the argument names found.

    Raises AssertionError with a descriptive message on malformed syntax.
    This models the actual rules the frontend's ICU parser applies (per the
    f377243 commit message): '{' and '}' are argument syntax UNLESS they
    appear inside a quoted literal span. A quoted span is opened by an
    apostrophe immediately followed by '{', '}', '#' or another apostrophe,
    and runs until the next (unescaped) apostrophe; a doubled apostrophe
    ('') is a literal apostrophe and never opens/closes quoting. A bare
    apostrophe not followed by a special character (e.g. "sensor's") is
    just literal text.
    """
    names: list[str] = []
    in_quote = False
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch == "'":
            if i + 1 < n and text[i + 1] == "'":
                i += 2
                continue
            if in_quote:
                in_quote = False
                i += 1
                continue
            if i + 1 < n and text[i + 1] in "{}#":
                in_quote = True
                i += 1
                continue
            i += 1
            continue
        if in_quote:
            i += 1
            continue
        if ch == "{":
            end = text.find("}", i + 1)
            nested = text.find("{", i + 1)
            if end == -1:
                raise AssertionError(
                    f"unterminated '{{' (no matching '}}') in {text!r}"
                )
            if nested != -1 and nested < end:
                raise AssertionError(
                    f"unescaped '{{' inside an argument at position {nested} "
                    f"in {text!r} - wrap literal braces in a quoted span "
                    f"(e.g. \"'{{...}}'\")"
                )
            arg_name = text[i + 1 : end].strip()
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", arg_name):
                raise AssertionError(f"malformed argument '{{{arg_name}}}' in {text!r}")
            names.append(arg_name)
            i = end + 1
            continue
        if ch == "}":
            raise AssertionError(f"stray '}}' with no matching '{{' in {text!r}")
        i += 1
    if in_quote:
        raise AssertionError(f"unterminated quoted literal (missing closing ') in {text!r}")
    return names


def _assert_no_markdown(path: str, text: str) -> None:
    for pattern in _MARKDOWN_PATTERNS:
        assert not pattern.search(text), (
            f"{path}: looks like markdown ({pattern.pattern}), but the config "
            f"flow frontend renders descriptions as plain text - it would show "
            f"literal '*', '`', '#' etc. to the user. Value: {text!r}"
        )


@pytest.fixture(scope="module")
def strings_json() -> dict[str, Any]:
    return _load_json(COMPONENT_DIR / "strings.json")


@pytest.fixture(scope="module")
def en_json() -> dict[str, Any]:
    return _load_json(COMPONENT_DIR / "translations" / "en.json")


@pytest.fixture(scope="module")
def de_json() -> dict[str, Any]:
    return _load_json(COMPONENT_DIR / "translations" / "de.json")


def test_translation_files_are_valid_json() -> None:
    """All three files must parse - a syntax error here breaks the whole integration."""
    for file in [
        COMPONENT_DIR / "strings.json",
        COMPONENT_DIR / "translations" / "en.json",
        COMPONENT_DIR / "translations" / "de.json",
    ]:
        _load_json(file)  # raises on invalid JSON


def test_en_translation_mirrors_strings_json(
    strings_json: dict[str, Any], en_json: dict[str, Any]
) -> None:
    """translations/en.json must stay a byte-for-byte mirror of strings.json.

    strings.json is the source of truth; en.json is what HA actually loads
    at runtime. If they drift, a fix applied to one silently doesn't apply
    to what users see.
    """
    assert en_json == strings_json


def test_de_translation_has_same_structure_as_en(
    en_json: dict[str, Any], de_json: dict[str, Any]
) -> None:
    """de.json must define exactly the same keys as en.json (only values differ).

    Catches a field added/renamed in English without updating German -
    HA would silently fall back to the (wrong-language) key or English text.
    """
    en_keys = {path for path, _ in _walk_strings(en_json)}
    de_keys = {path for path, _ in _walk_strings(de_json)}
    assert en_keys == de_keys, (
        f"missing in de.json: {en_keys - de_keys}\n"
        f"extra in de.json: {de_keys - en_keys}"
    )


@pytest.mark.parametrize("filename", ["strings.json", "translations/en.json", "translations/de.json"])
def test_icu_message_syntax_is_valid(filename: str) -> None:
    """Every string must be well-formed ICU MessageFormat, and use only known args.

    Regression guard for f377243 ("escape literal braces in info section
    translations"): a literal '{'/'}' in a Jinja/dict example that isn't
    wrapped in an ICU quoted literal span makes the *whole string* fail to
    parse on the frontend as "malformed argument", regardless of whether
    that string ever receives description_placeholders.
    """
    data = _load_json(COMPONENT_DIR / filename)
    for path, text in _walk_strings(data):
        try:
            names = _icu_argument_names(text)
        except AssertionError as err:
            pytest.fail(f"{filename}:{path}: {err}")
        for name in names:
            assert name in KNOWN_PLACEHOLDERS, (
                f"{filename}:{path}: argument {{{name}}} is not one of the "
                f"placeholders config_flow.py ever supplies ({KNOWN_PLACEHOLDERS})"
            )


@pytest.mark.parametrize("filename", ["strings.json", "translations/en.json", "translations/de.json"])
def test_no_markdown_in_any_translation_file(filename: str) -> None:
    """Regression guard for def8409 ("rewrite section descriptions as plain text").

    The config flow frontend does not run a markdown renderer over
    descriptions - **bold**, `code`, headings and bullet lists show up as
    literal punctuation, not formatting.
    """
    data = _load_json(COMPONENT_DIR / filename)
    for path, text in _walk_strings(data):
        _assert_no_markdown(f"{filename}:{path}", text)


async def test_ha_translation_loader_renders_config_flow_strings(
    hass: HomeAssistant,
) -> None:
    """End-to-end: load translations the same way HA's frontend does.

    This exercises the real loader (homeassistant.helpers.translation),
    not just the raw JSON, so it also catches structural mistakes hassfest
    would flag (e.g. a section referenced in strings.json that doesn't
    exist, or vice versa) without needing a running HA instance at all.
    """
    translations = await translation.async_get_translations(
        hass, "en", "config", integrations={DOMAIN}
    )
    assert any(
        key.endswith("step.user.title") and value == "Template Forecast"
        for key, value in translations.items()
    ), translations

    de_translations = await translation.async_get_translations(
        hass, "de", "config", integrations={DOMAIN}
    )
    assert any(
        key.endswith("step.user.title") and value == "Template Forecast"
        for key, value in de_translations.items()
    ), de_translations
    assert any(
        "Modus" in value
        for key, value in de_translations.items()
        if key.endswith("step.user.data.mode")
    ), de_translations


def test_every_info_section_key_used_by_config_flow_has_a_translation(
    strings_json: dict[str, Any],
) -> None:
    """Every "<field>_info_<mode>" section the code can render must have text.

    config_flow.py builds these keys dynamically (_info_section_key); a typo
    or a renamed mode there would otherwise silently show a section with no
    name/description in the UI instead of failing a test.
    """
    from custom_components.template_forecast.const import (
        CONF_ATTRIBUTE_TEMPLATE,
        CONF_STATE_TEMPLATE,
        MODE_GENERATE,
        MODE_TRANSFORM,
    )
    from custom_components.template_forecast.config_flow import _info_section_key

    expected_keys = {
        _info_section_key(field, mode)
        for field in (CONF_STATE_TEMPLATE, CONF_ATTRIBUTE_TEMPLATE)
        for mode in (MODE_GENERATE, MODE_TRANSFORM)
    }

    for step_id in ("generate", "transform"):
        sections = strings_json["config"]["step"][step_id].get("sections", {})
        relevant = {key for key in expected_keys if key.endswith(f"_{step_id}")}
        for key in relevant:
            assert key in sections, f"config.step.{step_id}.sections.{key} is missing"
            assert sections[key].get("name")
            assert sections[key].get("description")

    options_sections = strings_json["options"]["step"]["init"].get("sections", {})
    for key in expected_keys:
        assert key in options_sections, f"options.step.init.sections.{key} is missing"
