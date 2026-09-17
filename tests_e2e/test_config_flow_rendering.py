"""Drive the real config flow in a real browser and check what it renders.

tests/test_translations.py locks down the *source* JSON (valid ICU syntax,
no markdown). This file locks down the *result*: what a user actually sees
after Home Assistant parses that JSON, substitutes placeholders, and lays
it out in the collapsed "Info & examples" widget - a read-only Jinja code
box (a TemplateSelector with read_only=True, showing the example in a real
syntax-highlighted CodeMirror editor) plus markdown-rendered docs below it
(a field's data_description goes through ha-markdown). If a future change to
strings.json or config_flow.py ever produces garbled text, a stray literal
quote, a non-read-only box, or breaks ICU parsing outright (which surfaces
as a JS console error, not a Python exception), these are the tests that
would catch it - short of a human opening the flow in a browser, which is
the whole thing this suite exists to replace.
"""
from __future__ import annotations

EXPECTED_STATE_EXAMPLE_GENERATE = "{{ forecast[0].value }}"
EXPECTED_ATTRIBUTE_EXAMPLE_GENERATE = "{{ (10 + (20 - 10) * index / horizon) | round(2) }}"

# Note: the enclosing single quotes around the fenced-code Jinja/dict example
# in strings.json are ICU MessageFormat's literal-text escape syntax, not
# characters to display - HA's ICU parser consumes them and renders only
# what's between them (see tests/test_translations.py's _icu_argument_names
# docstring). The rendered markdown therefore shows the object example
# without surrounding quotes.
EXPECTED_ATTRIBUTE_HELPER_GENERATE_SUBSTRINGS = (
    "Evaluated once per time step to build the forecast list.",
    "0-based step",
    "total number of steps",
    '{{ {"time": forecast_time.isoformat(), "value": 10 + index, "condition": "sunny"} }}',
)


def _is_real_error(exc) -> bool:
    """Filter out browser/virtualized-list noise unrelated to our flow.

    HA's virtualized entity picker (lit-virtualizer) intermittently throws a
    benign, content-less "ResizeObserver loop ..." style exception that
    Chromium sometimes surfaces via `pageerror` as a bare non-Error object
    (stringifying to just "Object") - unrelated to whether our config flow
    or its ICU-formatted text rendered correctly.
    """
    message = str(exc)
    return bool(message) and message != "Object" and "ResizeObserver" not in message


def _open_template_forecast_flow(page):
    page.goto("/config/integrations/dashboard", wait_until="networkidle")
    page.get_by_role("button", name="Add integration").click()
    search = page.get_by_placeholder("Search for a brand name")
    search.wait_for(state="visible")
    search.fill("Template Forecast")
    page.get_by_text("Template Forecast (Helper)").click()
    page.get_by_role("button", name="OK").click()


def _expand_all_info_sections(page):
    sections = page.get_by_text("Info & examples")
    for i in range(sections.count()):
        sections.nth(i).click()


def test_generate_mode_info_sections_render_as_clean_plain_text(page):
    """The two collapsed "Info & examples" sections in Generate mode.

    Each section holds a read-only TemplateSelector pre-filled with a Jinja
    example (must render in a real, non-editable code editor - not a plain
    text field) plus that field's data_description as markdown docs below it
    (must render through ha-markdown - real <code> elements, not literal
    backticks). Regression coverage for: f377243 (unescaped braces broke ICU
    parsing), def8409 (a *section's own* description/name can never render
    markdown - this box works around that by using an ordinary field
    instead), and the ConstantSelector/BooleanSelector dead ends explored
    before landing on read_only=True (see config_flow.py's _info_content_key
    docstring).
    """
    page_errors = []
    page.on("pageerror", lambda exc: page_errors.append(str(exc)) if _is_real_error(exc) else None)

    _open_template_forecast_flow(page)
    page.locator("ha-dialog input[type=text], ha-dialog ha-textfield input").first.fill(
        "E2E Generate Forecast"
    )
    page.get_by_role("button", name="Submit").click()
    page.wait_for_selector("text=Planning horizon & templates")

    _expand_all_info_sections(page)
    page.wait_for_timeout(300)
    page.screenshot(path="tests_e2e/screenshots/generate_info_sections.png", full_page=True)

    panels = page.locator("ha-dialog ha-expansion-panel")
    assert panels.count() == 2, panels.count()

    code_editors = panels.locator("ha-code-editor")
    assert code_editors.count() == 2, code_editors.count()

    # Playwright's inner_text() comes up empty for CodeMirror 6's virtualized
    # viewport rendering - read its rendered text content (.cm-content)
    # directly instead, inside ha-code-editor's own shadow root.
    editor_texts = [
        code_editors.nth(i).evaluate(
            "el => el.shadowRoot?.querySelector('.cm-content')?.textContent ?? ''"
        )
        for i in range(2)
    ]
    assert any(EXPECTED_STATE_EXAMPLE_GENERATE in t for t in editor_texts), editor_texts
    assert any(EXPECTED_ATTRIBUTE_EXAMPLE_GENERATE in t for t in editor_texts), editor_texts

    # read_only must actually reach the underlying CodeMirror editor - not
    # just look right, but genuinely reject edits.
    for i in range(2):
        assert code_editors.nth(i).evaluate("el => el.readOnly") is True

    markdown_blocks = panels.locator("ha-markdown")
    assert markdown_blocks.count() == 2, markdown_blocks.count()
    page.wait_for_timeout(500)  # ha-markdown renders its content asynchronously
    helper_texts = [
        markdown_blocks.nth(i).evaluate("el => el.shadowRoot?.textContent ?? ''")
        for i in range(2)
    ]

    assert any("Available: forecast" in t for t in helper_texts), helper_texts
    for substring in EXPECTED_ATTRIBUTE_HELPER_GENERATE_SUBSTRINGS:
        assert any(substring in t for t in helper_texts), (substring, helper_texts)

    # Real markdown rendering means inline code became actual <code>
    # elements - the def8409 bug left literal backticks in the plain text
    # instead.
    for i in range(2):
        assert markdown_blocks.nth(i).locator("code").count() > 0
    for text in helper_texts:
        assert "`" not in text, text
        assert "```" not in text, text

    assert page_errors == [], page_errors


def test_transform_mode_shows_source_entity_via_real_placeholder_substitution(page):
    """The Transform step's description uses the one real dynamic placeholder.

    `"Source entity: {source_entity}"` is the only description in this
    integration that HA actually substitutes a runtime value into (see
    config_flow.py's description_placeholders). Driving this end to end
    confirms real placeholder substitution still works in the live
    frontend, not just that the ICU syntax around it is well-formed.
    """
    page_errors = []
    page.on("pageerror", lambda exc: page_errors.append(str(exc)) if _is_real_error(exc) else None)

    _open_template_forecast_flow(page)
    page.locator("ha-dialog input[type=text], ha-dialog ha-textfield input").first.fill(
        "E2E Transform Forecast"
    )
    page.get_by_text("Transform", exact=False).click()
    page.get_by_role("button", name="Submit").click()

    page.wait_for_selector("text=Source entity")
    page.get_by_text("Select an entity", exact=False).click()
    page.keyboard.type("sun.sun", delay=30)
    # Filtering for "sun.sun" also surfaces its attribute sensors (Next
    # dawn/dusk/...), which all render as "<name> Sun Sensor" - excluding
    # "Sensor" leaves only the sun.sun entity itself ("Sun Sun").
    sun_option = page.locator("ha-combo-box-item").filter(has_text="Sun").filter(
        has_not_text="Sensor"
    )
    sun_option.wait_for(state="visible")
    sun_option.click(force=True)
    page.get_by_role("button", name="Submit").click()

    page.wait_for_selector("text=Source entity: sun.sun")
    page.screenshot(path="tests_e2e/screenshots/transform_source_entity.png", full_page=True)

    assert page_errors == [], page_errors
