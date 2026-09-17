# Template Forecast (Home Assistant Helper)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=principat&repository=ha-template-forecast&category=integration)

A HACS custom integration that generates forecast sensors from Jinja2 templates –
as a "helper" through the normal UI (Settings → Devices & Services → Helpers → Create Helper).

Two modes:

- **Generate**: you specify a planning horizon (number of steps + step size). The
  attribute template is evaluated once per step and produces a `forecast` list
  (default name configurable).
- **Transform**: you select an existing entity whose list attribute (e.g. `forecast`)
  is run step by step through your template. You can build a new object in the process.

In both modes a **state template** is also required, which is rendered independently
of the attribute template and has access to the finished forecast result (variable `forecast`).

## Tests

```bash
pip install -r requirements_test.txt
pytest
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

[.github/workflows/test.yml](.github/workflows/test.yml) runs the suite on every pull
request, and [.github/workflows/release.yml](.github/workflows/release.yml) runs it
again as a gate before any release job.

## E2E UI tests (real Home Assistant, real browser)

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

## Releases

Versioning is automated with [semantic-release](https://semantic-release.gitbook.io/) via
[.github/workflows/release.yml](.github/workflows/release.yml). On every push to `master`,
commit messages are analyzed following [Conventional Commits](https://www.conventionalcommits.org/):

- `fix: ...` → patch release
- `feat: ...` → minor release
- `feat!: ...` or a `BREAKING CHANGE:` footer → major release

A release run bumps `custom_components/template_forecast/manifest.json`, updates
`CHANGELOG.md`, tags the commit, and publishes a GitHub Release with generated notes.
Commits that don't match a release type (e.g. `chore:`, `docs:`) don't trigger a release.

## Installation

1. Click the "Open in your Home Assistant instance" badge above (requires HACS and
   [My Home Assistant](https://www.home-assistant.io/integrations/my/) to be set up), or
   add `principat/ha-template-forecast` as a custom repository in HACS manually (category
   "Integration"), or copy the `custom_components/template_forecast` folder directly to
   `config/custom_components/`.
2. Restart Home Assistant.
3. Settings → Devices & Services → Helpers → "+ Create Helper" → "Template Forecast".

## Editing

Helpers that have already been created can be reopened at any time via the three dots
next to the helper → "Configure". The mode (Generate/Transform) is fixed once created,
all other fields (templates, horizon, update interval, target attribute, source) can be changed.

## Template Variables

### Generate mode, attribute template
- `index` – 0-based step index
- `horizon` – total number of steps
- `forecast_time` – timestamp of this step (datetime, UTC)

The template's return value becomes the forecast entry's `value`, giving
`{"time": <forecast_time as ISO string>, "value": <rendered result>}` – the
`"time"` key matches the format HAEO's own forecast sensors expect. If the
template renders a dict instead of a scalar, its keys are merged into the
entry (e.g. to add extra fields alongside `time`/`value`).

### Transform mode, attribute template
- `index` – position in the source list
- `item` – the complete original element (dict) from the source attribute
- `value` – `item.value`, if present (convenience)

### State template (both modes)
- `forecast` – the already computed result list (list of `{time, value}` in
  generate mode; in transform mode the original item's keys, whatever the
  source entity used, e.g. `{start_time, value}`)
- additionally in transform mode: `source` (state of the source entity), `source_forecast`
  (original list before the transformation)
- all normal Jinja functions (`states()`, `state_attr()`, `now()`, …) are available
  as usual.

## Default Sensor Properties

As with the built-in template sensor helper, the following can also be set (all optional):

- **Unit** (`unit_of_measurement`)
- **Device class** (`device_class`, dropdown with all valid `SensorDeviceClass` values)
- **State class** (`state_class`, `measurement` / `total` / `total_increasing`)
- **Icon** (icon picker, e.g. `mdi:currency-eur`)

These fields only affect the state/display of the entity, not the calculation –
for the individual forecast values in the attribute there is (deliberately, analogous to
most forecast conventions) no separate unit per list item.
