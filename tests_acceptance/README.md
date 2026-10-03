# Acceptance suite (pytest-bdd)

This suite is an executable version of the functional requirements in
[`docs/REQUIREMENTS.md`](../docs/REQUIREMENTS.md) §2, written as German
Gherkin feature files. The point of writing it this way, instead of as plain
pytest functions, is that the `.feature` files are plain text: if this
project is ever rebuilt on a different stack (even outside Python/Home
Assistant entirely), the scenarios stay valid as the specification. Only
`driver.py` - the one place that knows about Home Assistant config entries,
entity IDs, and async bridging - would need reimplementing.

Every feature file starts with a `# REQ 2.x` comment and carries an
`@REQ-2.x` tag matching the corresponding `docs/REQUIREMENTS.md` subsection.
**When a requirement in that document changes, update the matching feature
file in the same change** - that's the only sync mechanism, no tooling
enforces it.

## Layout

- `features/` - the Gherkin specification (German).
- `steps/` - step definitions, registered as pytest plugins via `conftest.py`.
  They only ever call `driver` fixture methods, never `hass` directly.
- `driver.py` - the single seam between Gherkin vocabulary and Home Assistant
  internals.
- `card_driver.py` - the seam for §2.8 (dashboard card), see below.
- `test_bindings/` - trivial `scenarios(...)` wiring, one file per feature
  file. Adding a new *Szenario* to an existing feature file needs no change
  here.

## §2.8: the dashboard card (TypeScript, run through Node)

The Forecast Chart card is browser code, so its scenarios cannot use the Home
Assistant `Driver`. `card_driver.py` runs the card's platform independent
logic - auto-detection, the mapping between the editor form and the stored
card configuration, and the building of the plotted lines - in Node through
the small JSON bridge `frontend/acceptance/bridge.ts` (bundled on the fly with
esbuild, one `node` call per step). The `.feature` file and the step names
stay implementation independent; only `card_driver.py` and the bridge know the
TypeScript code.

This needs Node.js and `npm ci` in `frontend/`. Locally the §2.8 scenarios are
**skipped** without them; when the `CI` environment variable is set (GitHub
Actions sets it) they **fail** instead, so the CI can never silently skip them.
How the chart and the editor look inside a real Home Assistant frontend is
covered by `tests_e2e/test_forecast_chart_card.py`, not here.

## Why steps are synchronous (and must stay that way)

pytest-bdd (8.1.0) has no native support for async step functions - an
`async def` step is simply never awaited. Home Assistant's test fixtures
(`hass`, `hass.config_entries.flow.async_configure()`, ...) are async,
though, driven by `pytest-asyncio` (`asyncio_mode = "auto"` in the project's
`pyproject.toml`). `Driver` bridges the two: `self.hass.loop.run_until_complete(coro)`
runs a coroutine to completion on the same event loop `pytest-asyncio` already
set up for the `hass` fixture, and `self.hass.async_block_till_done()` is
called after anything that can trigger listeners or background tasks (state
changes, timer fires, entry reloads). Don't try to make step functions
`async def` to "fix" this - the coroutine will just never run.

## Scope - what this suite deliberately does NOT cover

- **§2.6's UI rendering** (collapsed sections, CodeMirror syntax
  highlighting, `ha-markdown` rendering, en/de localization parity) - covered
  by `tests_e2e/` (real browser) and `tests/test_translations.py` (ICU/
  markdown/en-de sync). This suite only covers the one part of §2.6 that's
  observable black-box through the config/options flow API: that the
  collapsed info-section placeholders never end up in the stored
  configuration, even when driven directly (bypassing the frontend).
- **§2.7** (HACS distribution/installation) - not automatable via
  `pytest-homeassistant-custom-component` (no real HACS install, no real
  onboarding, no real badge click). Left as a manual/documentation-level
  concern.

## A documented simplification

`Driver.restart()` simulates a Home Assistant restart by unloading and
reloading the config entry within the *same* `hass` test instance, rather
than tearing down and rebuilding the whole fixture. This still exercises the
real `RestoreEntity`/`RestoreStateData` machinery (the in-memory cache of the
entity's last written state), which is what §2.4's restore-state guarantee
is actually about - it's cheaper than a full fixture rebuild and wasn't worth
the extra complexity for what this requirement observably promises.

## Running

```bash
pip install -r requirements_acceptance.txt
python -m pytest tests_acceptance -v
```

It's also included in `testpaths` in `pyproject.toml`, so a bare
`python -m pytest` runs it alongside `tests/`.
