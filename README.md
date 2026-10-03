# Template Forecast (Home Assistant Helper)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=principat&repository=ha-template-forecast&category=integration)

**English** | [Deutsche Version](#deutsch) (further down in this file)

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

### Forecast Chart card

The integration ships a dashboard card that plots forecast sensors (Template Forecast, HAEO,
EPEX Spot, ... - any entity with a list attribute) as a time series. Add it via Dashboard →
Edit → Add card → **Forecast Chart**. Pick the entity and the list attribute, time field and
value field are pre-selected; add more entities or more value fields, and use the *Details*
section per field for a scaling factor, name, color and more. The configuration can be
changed at any time (⋮ → Edit). Details and the YAML format:
[`frontend/README.md`](frontend/README.md).

> The card is provided by the integration, so it becomes available once the integration is
> loaded, i.e. as soon as at least one Template Forecast helper exists. Restart Home Assistant
> after the first install, and reload the browser page if the card does not show up.

**Preview:** the card picker shows a live preview (using the first entity with a list attribute
it finds), and the card editor shows the chart while you configure it, so every change is
visible immediately.

![Forecast Chart card showing charging cost, maximum charging power, outdoor temperature and target state of charge as step lines on two Y axes](docs/images/forecast-chart-card.png)

*Screenshot rendered with sample data: four series on two Y axes (ct/kWh left; kW, °C and %
right), step lines and the dotted "now" marker.*

### Examples

Ready-to-adapt, real-world configurations for use with
[HAEO](https://haeo.io) (feed-in during negative prices, EV availability and
charging target, wallbox power limit, solar charge lateness) are in
[`examples/`](examples/) - [English](examples/en/README.md) |
[Deutsch](examples/de/README.md). Have one to share? Open an issue with the
[Example template](https://github.com/principat/ha-template-forecast/issues/new?template=example.yml).

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
- `tests_acceptance/` - pytest-bdd acceptance suite: German Gherkin feature
  files that are an executable version of `docs/REQUIREMENTS.md`'s
  functional requirements, deliberately kept implementation-agnostic (see
  its own README for the pattern and its scope).
- `frontend/` - source of the Forecast Chart dashboard card (TypeScript, own
  toolchain, tests and README). The build output lives in
  `custom_components/template_forecast/www/` and is committed; the only Python link is
  `custom_components/template_forecast/frontend.py`.
- `examples/` - documented example configurations, one folder per language
  (`examples/en/`, `examples/de/`). A new language gets its own folder with
  the same file structure.
- `.github/ISSUE_TEMPLATE/` - issue forms for bug reports (`bug` label, plus a
  `version: x.y.z` label set by `.github/workflows/label-version.yml`) and
  shared examples (`example` label).
- `docs/REQUIREMENTS.md` - the maintained requirements specification for this
  project (functional requirements + the technical implementation choices),
  kept up to date as new requirements come in. Check it before making
  behavioral changes, and update it alongside the code when a requirement
  changes.

### Tests

```bash
pip install -r requirements_acceptance.txt
python -m pytest
```

This runs entirely in-process against a mocked Home Assistant core
([pytest-homeassistant-custom-component](https://github.com/MatthewFlamm/pytest-homeassistant-custom-component)) -
no real HA install, no restart, no manual click-through needed to check a change.
(`requirements_acceptance.txt` layers on top of `requirements_test.txt`; use
that alone if you only care about `tests/`.)

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
- `tests_acceptance/`: pytest-bdd acceptance suite exercising
  `docs/REQUIREMENTS.md`'s functional requirements as German Gherkin
  scenarios, through the same config-flow/sensor API as the tests above but
  behind an implementation-hiding `Driver` (see `tests_acceptance/README.md`).

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

---

<a id="deutsch"></a>

# Deutsch

[English version](#template-forecast-home-assistant-helper) (oben in dieser Datei)

Template Forecast ist eine HACS-Integration, mit der du Forecast-Sensoren aus
eigenen Jinja2-Templates baust, komplett über die Home-Assistant-Oberfläche -
ohne YAML.

> Dieser Abschnitt enthält die Anleitung für Anwender. Der Bereich
> „For developers" (Repository-Aufbau, Tests, Releases) gilt für beide Sprachen
> und steht nur auf Englisch weiter oben.

## Für Anwender

### Was ist das?

Viele Integrationen (Wetter, Strompreise, ...) liefern eine „Prognose": einen
Sensor, dessen State der aktuelle Wert ist und der in einem Attribut eine Liste
künftiger Werte enthält. Mit **Template Forecast** baust du so einen Sensor
selbst, mit Jinja2-Templates im normalen Dialog „Helfer erstellen" - genauso wie
beim eingebauten Template-Helfer.

Es gibt zwei Modi:

- **Generate**: Du legst einen Planungshorizont fest (Anzahl Schritte +
  Schrittweite, z. B. „24 Schritte à 60 Minuten"). Dein Template wird einmal
  pro Schritt ausgewertet und erzeugt die `forecast`-Liste (der Attributname
  ist konfigurierbar).
- **Transform**: Du wählst eine bestehende Entität, deren Listen-Attribut
  (z. B. `forecast`) du umwandeln willst - dein Template läuft einmal pro
  Listeneintrag. Nützlich für Einheitenumrechnung, das Verknüpfen einer
  Prognose mit einem anderen Sensor, das Umbenennen von Feldern usw.

In beiden Modi ist zusätzlich ein **State-Template** nötig. Es wird separat
ausgewertet, nachdem die Forecast-Liste erstellt wurde, und kann über die
Variable `forecast` auf das fertige Ergebnis zugreifen - der State des Sensors
kann also z. B. „der Wert der nächsten Stunde" oder eine Auswertung über die
ganze Liste sein.

### Wofür ist das nützlich?

- Du kennst Jinja2 (aus Template-Helfern/-Sensoren von Home Assistant) und
  willst weder YAML lernen, noch eine komplette Integration schreiben, noch
  einen `template:`-Block in der Konfiguration pflegen für etwas, das
  eigentlich ein „Helfer" ist.
- Du brauchst einen Forecast-Sensor (State + Listen-Attribut) für eigene
  Dashboards, Automationen oder Energie-Tools (z. B. im `time`/`value`-Format,
  das viele Tools erwarten), basierend auf Daten oder Logik, die Home Assistant
  nicht von Haus aus liefert.
- Du willst einen bestehenden Forecast-Sensor einer anderen Integration
  umformen oder kombinieren, ohne dessen Aktualisierungslogik zu duplizieren.

### Wie benutze ich es?

1. **Installieren** über HACS (empfohlen) oder manuell:
   - Auf das „Open in your Home Assistant instance"-Badge oben klicken
     (benötigt HACS und
     [My Home Assistant](https://www.home-assistant.io/integrations/my/)),
     oder `principat/ha-template-forecast` in HACS manuell als eigenes
     Repository hinzufügen (Kategorie „Integration").
   - Alternativ den Ordner `custom_components/template_forecast` direkt nach
     `config/custom_components/` kopieren.
   - Home Assistant neu starten.
2. **Helfer erstellen**: Einstellungen → Geräte & Dienste → Helfer → „+ Helfer
   erstellen" → „Template Forecast".
3. **Namen** und **Modus** (Generate oder Transform) wählen. Der Modus lässt
   sich später nicht mehr ändern - bei falscher Wahl den Helfer löschen und
   neu anlegen.
4. State-Template und Attribut-Template ausfüllen. Über jedem Template-Feld
   gibt es einen eingeklappten Bereich „Info & examples" mit einem
   kopierfertigen Beispiel und einer Beschreibung der in diesem Feld/Modus
   verfügbaren Variablen.
5. Optional Einheit, Geräteklasse, Zustandsklasse und Icon setzen - diese
   wirken sich nur auf die Darstellung des *States* aus, nicht auf die
   einzelnen Forecast-Werte.
6. Speichern. Der neue Sensor erscheint sofort und wird automatisch neu
   berechnet, sobald sich eine in den Templates referenzierte Entität ändert,
   zusätzlich periodisch im eingestellten Aktualisierungsintervall als
   Sicherheitsnetz.

Jeden Helfer kannst du später wieder öffnen (drei Punkte → „Konfigurieren"),
um Templates, Horizont, Aktualisierungsintervall, Ziel-Attribut oder Quelle zu
ändern - alles außer dem Modus.

#### Referenz der Template-Variablen

**Generate-Modus, Attribut-Template:**
- `index` - 0-basierter Schrittindex
- `horizon` - Gesamtzahl der Schritte
- `forecast_time` - Zeitstempel dieses Schritts (datetime, UTC)

Der Rückgabewert des Templates wird zum `value` des Forecast-Eintrags, also
`{"time": <forecast_time als ISO-String>, "value": <Ergebnis>}` - der Schlüssel
`"time"` entspricht dem Format, das HAEOs eigene Forecast-Sensoren erwarten.
Liefert das Template ein Dict statt eines Skalars, werden dessen Schlüssel in
den Eintrag übernommen (z. B. für zusätzliche Felder neben `time`/`value`).

**Transform-Modus, Attribut-Template:**
- `index` - Position in der Quellliste
- `item` - das vollständige Originalelement (Dict) aus dem Quellattribut
- `value` - `item.value`, falls vorhanden (Komfortvariable)

**State-Template (beide Modi):**
- `forecast` - die bereits berechnete Ergebnisliste (Liste aus `{time, value}`
  im Generate-Modus; im Transform-Modus die Schlüssel des Originaleintrags,
  was immer die Quelle verwendet, z. B. `{start_time, value}`)
- zusätzlich im Transform-Modus: `source` (State der Quellentität),
  `source_forecast` (Originalliste vor der Umwandlung)
- alle üblichen Jinja-Funktionen (`states()`, `state_attr()`, `now()`, ...)
  stehen wie gewohnt zur Verfügung.

#### Standard-Sensoreigenschaften

Wie beim eingebauten Template-Sensor-Helfer lassen sich folgende Eigenschaften
setzen (alle optional):

- **Einheit** (`unit_of_measurement`)
- **Geräteklasse** (`device_class`, Dropdown mit allen gültigen
  `SensorDeviceClass`-Werten)
- **Zustandsklasse** (`state_class`, `measurement` / `total` /
  `total_increasing`)
- **Icon** (Icon-Auswahl, z. B. `mdi:currency-eur`)

### Forecast-Diagramm-Karte

Die Integration liefert eine Dashboard-Karte mit, die Forecast-Sensoren (Template Forecast,
HAEO, EPEX Spot, ... - jede Entität mit Listenattribut) als Zeitreihe darstellt. Hinzufügen
über Dashboard → Bearbeiten → Karte hinzufügen → **Forecast Chart**. Entität wählen, Listen-
Attribut, Zeitfeld und Wertefeld sind vorausgewählt; weitere Entitäten oder Wertefelder lassen
sich hinzufügen, und im Bereich *Details* je Feld stehen Skalierungsfaktor, Name, Farbe u. a.
bereit. Die Konfiguration kann jederzeit geändert werden (⋮ → Bearbeiten). Details und
YAML-Format: [`frontend/README.md`](frontend/README.md).

> Die Karte wird von der Integration bereitgestellt und ist verfügbar, sobald die Integration
> geladen ist, also sobald mindestens ein Template-Forecast-Helper existiert. Nach der ersten
> Installation Home Assistant neu starten und die Seite im Browser neu laden, falls die Karte
> nicht erscheint.

**Vorschau:** Der Karten-Dialog zeigt eine Live-Vorschau (mit der ersten gefundenen Entität
mit Listenattribut), und der Karten-Editor zeigt das Diagramm während der Konfiguration, sodass
jede Änderung sofort sichtbar ist.

![Forecast-Chart-Karte mit Ladekosten, maximaler Ladeleistung, Außentemperatur und Ziel-Ladezustand als Stufenlinien auf zwei Y-Achsen](docs/images/forecast-chart-card.png)

*Screenshot mit Beispieldaten: vier Serien auf zwei Y-Achsen (ct/kWh links; kW, °C und %
rechts), Stufenlinien und gepunktete „Jetzt“-Markierung.*

### Beispiele

Praxisnahe, anpassbare Konfigurationen für die Verwendung mit
[HAEO](https://haeo.io) (Einspeisung bei negativen Preisen, E-Auto-Verfügbarkeit
und Ladeziel, Wallbox-Leistungsbegrenzung, Solar-Ladeverzögerung) findest du in
[`examples/`](examples/) - [Deutsch](examples/de/README.md) |
[English](examples/en/README.md). Du hast eine eigene Konfiguration zu teilen?
Eröffne ein Issue mit der
[Vorlage „Example"](https://github.com/principat/ha-template-forecast/issues/new?template=example.yml).
