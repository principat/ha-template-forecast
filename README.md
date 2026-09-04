# Template Forecast (Home Assistant Helper)

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

8 tests cover the config flow (generate/transform/options, including rejection of invalid
templates) and the sensor calculation logic (linear ramp, per-item transformation,
automatic recalculation on source update, empty source).

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

1. Add as a custom repository in HACS (category "Integration"), or copy the
   `custom_components/template_forecast` folder manually to `config/custom_components/`.
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

### Transform mode, attribute template
- `index` – position in the source list
- `item` – the complete original element (dict) from the source attribute
- `value` – `item.value`, if present (convenience)

### State template (both modes)
- `forecast` – the already computed result list (list of `{datetime, value}`)
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
