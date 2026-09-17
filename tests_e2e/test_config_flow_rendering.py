"""Drive the real config flow in a real browser and check what it renders.

tests/test_translations.py locks down the *source* JSON (valid ICU syntax,
no markdown). This file locks down the *result*: what a user actually sees
after Home Assistant parses that JSON, substitutes placeholders, and lays
it out in the collapsed "Info & examples" widget. If a future change to
strings.json ever produces garbled text, a stray literal quote, or breaks
ICU parsing outright (which surfaces as a JS console error, not a Python
exception), these are the tests that would catch it - short of a human
opening the flow in a browser, which is the whole thing this suite exists
to replace.
"""
from __future__ import annotations

# Note: the enclosing single quotes in strings.json are ICU MessageFormat's
# literal-text escape syntax, not characters to display - HA's ICU parser
# consumes them and renders only what's between them. The rendered DOM
# therefore shows the Jinja/dict example WITHOUT surrounding quotes; if a
# stray quote is missing or the parser fails, the visible text would either
# still carry the quote (parser fell back to raw text) or omit the example
# entirely (parser choked) - which is exactly what these two constants
# would then fail to match.
EXPECTED_STATE_INFO_GENERATE = (
    "Defines the value shown as the sensor's own state. Available: forecast, "
    "the already computed result list from the attribute template below, "
    "e.g. forecast[0].value. Example: {{ forecast[0].value }}"
)
EXPECTED_ATTRIBUTE_INFO_GENERATE = (
    "Evaluated once per time step to build the forecast list. Available: "
    "index (0-based step), horizon (total number of steps), forecast_time "
    "(datetime of this step, UTC). Simple value example: {{ (10 + (20 - 10) "
    "* index / horizon) | round(2) }}. To set multiple fields per entry, "
    'such as a custom time, return an object instead: {{ {"time": '
    'forecast_time.isoformat(), "value": 10 + index, "condition": "sunny"} }}'
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

    Regression coverage for two bugs that were only caught before by
    manually opening this exact screen: f377243 (unescaped braces made the
    whole description fail ICU parsing) and def8409 (markdown syntax like
    backticks/code fences showing up as literal characters, because the
    section widget renders plain text, not markdown).
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
    rendered = [panels.nth(i).inner_text().strip() for i in range(panels.count())]

    # Each panel renders as "<name>\n<description>" - strip the repeated
    # "Info & examples" header line before comparing the description body.
    bodies = [text.split("\n", 1)[1].strip() if "\n" in text else "" for text in rendered]

    assert EXPECTED_STATE_INFO_GENERATE in bodies, bodies
    assert EXPECTED_ATTRIBUTE_INFO_GENERATE in bodies, bodies

    # Markdown that didn't render (the def8409 bug) would leave literal
    # backticks/asterisks/code-fences sitting in the text.
    for body in bodies:
        assert "```" not in body, body
        assert "`" not in body, body
        assert "**" not in body, body

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
