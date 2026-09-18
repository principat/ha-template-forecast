# Template Forecast (Home Assistant Helper)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=principat&repository=ha-template-forecast&category=integration)

A HACS custom integration that lets you build forecast sensors from your own
Jinja2 templates, entirely through the Home Assistant UI - no YAML required.

---

## For users

### What is this?

Many integrations (weather, energy prices, ...) expose a "forecast": a sensor
whose state is the current value, plus a list of future values in an
attribute. **Template Forecast** lets you build a sensor like that yourself,
using Jinja2 templates you write in the normal "Create Helper" dialog - the
same way you'd create a built-in Template Helper.

Two modes are available:

- **Generate**: you define a planning horizon (number of steps + step size,
  e.g. "24 steps of 60 minutes"). Your template is evaluated once per step to
  produce a `forecast` list (the attribute name is configurable).
- **Transform**: you pick an existing entity whose list attribute (e.g.
  `forecast`) you want to transform - your template runs once per item of
  that list. Useful for unit conversions, combining a forecast with another
  sensor, re-labeling fields, etc.

In both modes, a **state template** is also required. It's rendered
separately, after the forecast list is built, and has access to the finished
result via the `forecast` variable - so the sensor's state can be, say, "the
next hour's value" or an aggregate over the whole list.

### Why would I use this?

- You already know Jinja2 (from Home Assistant's Template Helper/sensors) and
  don't want to learn YAML, write a full custom integration, or maintain a
  `template:` block in your configuration for something that's really a
  "helper".
- You want a forecast-shaped sensor (state + list attribute) for your own
  dashboards, automations, or energy tools (e.g. compatible with the
  `time`/`value` shape many forecast-consuming tools expect), based on data
  or logic Home Assistant doesn't provide out of the box.
- You want to reshape or combine an existing forecast sensor from another
  integration without duplicating its update logic.

### How do I use it?

1. **Install** via HACS (recommended) or manually:
   - Click the "Open in your Home Assistant instance" badge above (requires
     HACS and [My Home Assistant](https://www.home-assistant.io/integrations/my/)),
     or add `principat/ha-template-forecast` as a custom repository in HACS
     manually (category "Integration").
   - Alternatively, copy the `custom_components/template_forecast` folder
     directly into `config/custom_components/`.
   - Restart Home Assistant.
2. **Create a helper**: Settings → Devices & Services → Helpers → "+ Create
   Helper" → "Template Forecast".
3. Pick a **name** and a **mode** (Generate or Transform). The mode can't be
   changed later - if you pick wrong, delete the helper and create a new one.
4. Fill in the state template and attribute template. Each template field has
   a collapsed "Info & examples" section above it with a ready-to-copy
   example and a description of the variables available in that field/mode -
   expand it if you're unsure what to write.
5. Optionally set a unit, device class, state class, and icon for the sensor
   - these only affect how the sensor's *state* is displayed, not the
     individual forecast values.
6. Save. The new sensor appears immediately and recalculates automatically
   whenever any entity your templates reference changes, plus periodically
   on the configured update interval as a safety net.

You can reopen any helper later (three dots next to it → "Configure") to
change templates, horizon, update interval, target attribute, or source -
everything except the mode.

#### Template variables reference

**Generate mode, attribute template:**
- `index` - 0-based step index
- `horizon` - total number of steps
- `forecast_time` - timestamp of this step (datetime, UTC)

The template's return value becomes the forecast entry's `value`, giving
`{"time": <forecast_time as ISO string>, "value": <rendered result>}` - the
`"time"` key matches the format HAEO's own forecast sensors expect. If the
template renders a dict instead of a scalar, its keys are merged into the
entry (e.g. to add extra fields alongside `time`/`value`).

**Transform mode, attribute template:**
- `index` - position in the source list
- `item` - the complete original element (dict) from the source attribute
- `value` - `item.value`, if present (convenience)

**State template (both modes):**
- `forecast` - the already computed result list (list of `{time, value}` in
  generate mode; in transform mode the original item's keys, whatever the
  source entity used, e.g. `{start_time, value}`)
- additionally in transform mode: `source` (state of the source entity),
  `source_forecast` (original list before the transformation)
- all normal Jinja functions (`states()`, `state_attr()`, `now()`, ...) are
  available as usual.

#### Default sensor properties

As with the built-in template sensor helper, the following can also be set
(all optional):

- **Unit** (`unit_of_measurement`)
- **Device class** (`device_class`, dropdown with all valid `SensorDeviceClass` values)
- **State class** (`state_class`, `measurement` / `total` / `total_increasing`)
- **Icon** (icon picker, e.g. `mdi:currency-eur`)

---

## For developers

This section covers the repo layout, how to test and release changes, and
conventions to follow so contributions fit the existing project.

### Repository layout

- `custom_components/template_forecast/` - the integration itself
  (`config_flow.py`, `sensor.py`, `const.py`, `strings.json` +
  `translations/`).
- `tests/` - mocked unit/flow tests (fast, no real HA install).
- `tests_e2e/` - real-browser end-to-end tests against a real, throwaway HA
  instance.
- `docs/REQUIREMENTS.md` - the maintained requirements specification for this
  project (functional requirements + the technical implementation choices),
  kept up to date as new requirements come in. Check it before making
  behavioral changes, and update it alongside the code when a requirement
  changes.

### Tests

```bash
pip install -r requirements_test.txt
python -m pytest
```

This runs entirely in-process against a mocked Home Assistant core
([pytest-homeassistant-custom-component](https://github.com/MatthewFlamm/pytest-homeassistant-custom-component)) -
no real HA install, no restart, no manual click-through needed to check a change.

- `tests/test_config_flow.py` / `tests/test_sensor.py`: the config/options flow
  (generate/transform, rejection of invalid or failing templates) and the
  sensor calculation logic (linear ramp, per-item transformation, automatic
  recalculation on source update, empty source).
- `tests/test_translations.py`: catches config flow *UI* regressions that the
  flow logic tests above can't see - malformed ICU MessageFormat syntax
  (unescaped braces in a Jinja/dict example breaking the whole string),
  markdown showing up as literal characters (the section description widget
  renders plain text, not markdown), `en`/`de` translations drifting out of
  sync, and translation keys referenced by `config_flow.py` that don't exist.
  It also loads the strings through HA's real translation loader, the same
  path the frontend uses.

Always run this repo's pytest via `python -m pytest`, not the bare `pytest`
entry point - the latter doesn't add the repo root to `sys.path`, which
breaks the `from custom_components.template_forecast...` imports used
throughout the tests.

[.github/workflows/test.yml](.github/workflows/test.yml) runs the suite on every pull
request, and [.github/workflows/release.yml](.github/workflows/release.yml) runs it
again as a gate before any release job.

### E2E UI tests (real Home Assistant, real browser)

`tests/test_translations.py` checks that the config-flow strings are
well-formed; it doesn't see how they actually render. `tests_e2e/` closes
that gap: it boots a real, throwaway `hass` instance (with the real
`home-assistant-frontend` static assets, not a mock) and drives the actual
config flow with headless Chromium via [Playwright](https://playwright.dev/python/).
It automates the same install → restart → click-through-the-flow loop you'd
otherwise do by hand, so a future change to `strings.json` or `config_flow.py`
gets checked the same way before you ever open a browser yourself.

```bash
pip install -r requirements_e2e.txt
python -m playwright install --with-deps chromium  # once, downloads Chromium
pytest tests_e2e
```

It onboards a fresh instance once per session, then drives both the
Generate and Transform config-flow paths, expanding every collapsed "Info &
examples" section and asserting the *rendered* text - not just the source
JSON - matches exactly, with no leftover markdown or JS console errors.
Screenshots of each state are written to `tests_e2e/screenshots/` for a
quick visual look without opening a browser at all.

This suite is intentionally kept separate from `tests/` (its own
`pytest.ini`, disabling the `tests/` suite's HA-mock and socket-blocking
plugins) since it needs the extra `home-assistant-frontend`/Playwright
dependencies and a Chromium download, and a full boot-and-onboard cycle
takes longer than the mocked unit tests. It isn't part of the release gate;
[.github/workflows/test-e2e.yml](.github/workflows/test-e2e.yml) runs it on
every pull request and uploads the screenshots as a build artifact.

When changing `config_flow.py` or its translations in a way that affects
layout or adds new UI elements, extend
`tests_e2e/test_config_flow_rendering.py` rather than trusting the
JSON-level ICU/markdown checks alone.

### Translations

`strings.json` and `translations/*.json` are parsed by the frontend as **ICU
MessageFormat**, not Python `str.format`-style doubled braces. A literal
`{`/`}` in an example or description must be wrapped in an ICU quoted
literal span (`'...'`, opened by an apostrophe immediately followed by
`{`/`}`/`#`), not escaped by doubling. Keep `en` and `de` structurally in
sync - `tests/test_translations.py` enforces this.

### Releases

Versioning is automated with [semantic-release](https://semantic-release.gitbook.io/) via
[.github/workflows/release.yml](.github/workflows/release.yml). On every push to `master`,
commit messages are analyzed following [Conventional Commits](https://www.conventionalcommits.org/):

- `fix: ...` → patch release
- `feat: ...` → minor release
- `feat!: ...` or a `BREAKING CHANGE:` footer → major release
- other types (`chore:`, `docs:`, `ci:`, ...) don't trigger a release

A release run bumps `custom_components/template_forecast/manifest.json`, updates
`CHANGELOG.md`, tags the commit, and publishes a GitHub Release with generated notes.
The release job only runs if the test suite passes (`needs: test`).

**Use commit types deliberately** - if you want a change committed without
publishing a new version (e.g. docs, CI tweaks, non-user-facing chores), use
a non-releasing type like `docs:`/`chore:`/`ci:`.
