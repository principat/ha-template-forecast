# Anforderungsspezifikation – Template Forecast (HA Helper)

Dieses Dokument fasst alle fachlichen und technischen Anforderungen an das Projekt
`ha-template-forecast` zusammen. Es dient als Referenz, um das Projekt bei Bedarf
komplett neu aufzusetzen, und wird bei neuen Anforderungen fortlaufend gepflegt.

Der Bereich **Funktionale Anforderungen** beschreibt, *was* die Integration können muss,
unabhängig davon, wie sie technisch umgesetzt ist. Der Bereich **Technische Aspekte**
beschreibt die *konkrete* Umsetzung (Frameworks, Bibliotheken, CI/CD, gewählte
Implementierungs-Tricks). Beim Neuerstellen kann der technische Teil bewusst
weggelassen oder durch eine andere Lösung ersetzt werden, ohne die fachlichen
Anforderungen zu verändern.

> **Pflegehinweis:** Wenn neue Anforderungen hinzukommen oder sich bestehende ändern,
> wird dieses Dokument entsprechend aktualisiert (neuer Abschnitt oder Ergänzung eines
> bestehenden). Erledigt = "im aktuellen Code umgesetzt", nicht "irgendwann gewünscht".

---

## 1. Zweck des Projekts

Eine Home-Assistant-Integration, die es erlaubt, **Forecast-Sensoren** (Sensoren mit
einer Liste von Vorhersagewerten als Attribut, analog zu Wetter-/Preis-Forecast-Sensoren)
komplett über die normale HA-Oberfläche zu erstellen und zu konfigurieren – ohne YAML,
als "Helper" (Settings → Devices & Services → Helpers → "+ Create Helper").

Die eigentliche Berechnungslogik der Vorhersagewerte wird vom Nutzer selbst als
**Jinja2-Template** angegeben, wodurch die Integration generisch für beliebige
Berechnungen einsetzbar ist (z. B. Preis-Rampen, Umrechnungen bestehender Forecasts,
Kombinationen mehrerer Quellen).

Zielgruppe: Home-Assistant-Nutzer, die Jinja-Templates beherrschen (vergleichbar mit
Nutzern des eingebauten "Template"-Helpers), aber keine eigene Custom-Component
schreiben wollen.

---

## 2. Funktionale Anforderungen

### 2.1 Zwei Betriebsmodi

Beim Erstellen eines Helpers wird zwingend einer von zwei Modi gewählt. **Der Modus ist
nach dem Erstellen nicht mehr änderbar** (nur durch Löschen + Neuanlage), da er die
zugrundeliegende Berechnungslogik bestimmt.

- **Generate-Modus:** Erzeugt eine Vorhersage über einen festen Planungshorizont.
  Der Nutzer gibt an:
  - Anzahl der Schritte (Horizon Steps)
  - Schrittweite in Minuten (Step Minutes)
  Das Attribut-Template wird für jeden Schritt einmal ausgewertet.

- **Transform-Modus:** Transformiert eine bereits bestehende Forecast-Liste (Attribut
  einer anderen Entity, z. B. `forecast`). Der Nutzer wählt:
  - eine Quell-Entity (Entity Picker)
  - den Namen des Quell-Attributs (Text, z. B. `forecast`)
  Das Attribut-Template wird für jedes Element der Quellliste einmal ausgewertet.

### 2.2 Templates

Beide Modi benötigen zwei Templates:

- **Attribut-Template** (Pflichtfeld): erzeugt/transformiert die einzelnen
  Vorhersage-Einträge.
  - Generate-Modus, verfügbare Variablen:
    - `index` – 0-basierter Schrittindex
    - `horizon` – Gesamtzahl der Schritte
    - `forecast_time` – Zeitstempel dieses Schritts (datetime, UTC)
  - Transform-Modus, verfügbare Variablen:
    - `index` – Position in der Quellliste
    - `item` – das komplette Original-Element (dict) aus dem Quellattribut
    - `value` – `item.value`, falls vorhanden (Komfort-Variable)
  - Rückgabewert:
    - Skalarer Wert → wird zum `value`-Feld des Eintrags:
      `{"time": <ISO-Zeitstempel>, "value": <Ergebnis>}` (Generate) bzw. Original-Item
      mit überschriebenem `value` (Transform).
    - Dict-Wert → dessen Keys werden in den Eintrag gemergt (z. B. um zusätzliche
      Felder neben `time`/`value` zu ergänzen).
  - Das Zeitformat `"time"` muss kompatibel mit dem sein, was andere
    Forecast-Sensor-Konventionen (z. B. HAEO) erwarten.

- **State-Template** (Pflichtfeld): wird unabhängig vom Attribut-Template gerendert und
  bestimmt den Entity-**Zustand** (State). Verfügbare Variablen (beide Modi):
  - `forecast` – die bereits berechnete Ergebnisliste
  - zusätzlich im Transform-Modus: `source` (State der Quell-Entity),
    `source_forecast` (Original-Liste vor der Transformation)
  - alle normalen Jinja-Funktionen (`states()`, `state_attr()`, `now()`, …) sind
    verfügbar.

- Templates müssen **serverseitig validiert** werden, bevor der Helper angelegt/
  gespeichert wird:
  - Syntaktische Prüfung (ungültiges Jinja → Fehler am jeweiligen Feld).
  - Semantische Prüfung durch einen Testrender mit realitätsnahen Platzhalterwerten
    (z. B. Template referenziert eine Variable, die nur im jeweils anderen Modus
    existiert) → Fehler am jeweiligen Feld inkl. verständlicher Fehlermeldung aus der
    Jinja-Exception.

### 2.3 Weitere Konfigurationsfelder

- **Zielattribut-Name** (Target Attribute): Name des Attributs, unter dem die
  Vorhersageliste am Sensor abgelegt wird (Standard: `forecast`, änderbar).
- **Update-Intervall** (Minuten, Ganzzahl ≥ 1): periodische Neuberechnung, unabhängig
  von zustandsgetriebenen Neuberechnungen.
- Sensor-Anzeigeeigenschaften (alle optional, analog zum eingebauten
  Template-Sensor-Helper):
  - **Einheit** (unit_of_measurement, Freitext)
  - **Device Class** (Dropdown, alle gültigen `SensorDeviceClass`-Werte + "keine")
  - **State Class** (Dropdown: measurement / total / total_increasing / keine)
  - **Icon** (Icon-Picker)
  - Diese Felder wirken sich **nur auf Anzeige/State** aus, nicht auf die Berechnung.
    Für einzelne Forecast-Werte im Attribut gibt es bewusst **keine** separate Einheit
    pro Listeneintrag (analog zu üblichen Forecast-Konventionen).

### 2.4 Automatische Neuberechnung

Der Sensor muss sich automatisch neu berechnen bei:
- Zustandsänderungen aller Entities, die in den Templates referenziert werden
  (automatische Abhängigkeitserkennung, keine manuelle Angabe nötig).
- Im Transform-Modus zusätzlich bei jeder Änderung der Quell-Entity.
- Periodisch gemäß dem konfigurierten Update-Intervall (als Fallback/Sicherheitsnetz).
- Der letzte bekannte Zustand wird über Neustarts hinweg wiederhergestellt
  (Restore-State), bis die erste echte Neuberechnung erfolgt ist.
- Eine leere oder fehlende Quellliste (Transform-Modus) darf nicht zum Absturz führen,
  sondern zu einer leeren Vorhersageliste (mit Warnung im Log).
- Rechenfehler in Templates dürfen den Sensor nicht zum Absturz bringen, sondern
  werden geloggt; der Sensor behält den letzten gültigen Zustand.

### 2.5 Bearbeitbarkeit nach dem Anlegen

Ein bereits erstellter Helper muss über die Standard-HA-Oberfläche (drei Punkte neben
dem Helper → "Configure") jederzeit nachbearbeitet werden können. Änderbar sind alle
Felder außer dem Modus (Templates, Horizon, Update-Intervall, Zielattribut,
Quell-Entity/-Attribut, Anzeigeeigenschaften). Eine Änderung muss die laufende
Entity automatisch neu laden (kein Neustart von Home Assistant nötig).

### 2.6 Bedienungshilfen im Konfigurationsdialog

- Zu jedem Template-Feld gehört ein **einklappbarer Info-Bereich** ("Info & examples"),
  der:
  - ein **nicht editierbares Beispiel-Template** in echter Code-Darstellung
    (Syntax-Highlighting) zeigt, passend zum aktuellen Modus.
  - eine **Beschreibung mit echter Markdown-Formatierung** (Inline-Code, Codeblöcke)
    enthält, welche Variablen verfügbar sind und wie der Rückgabewert interpretiert
    wird.
  - standardmäßig eingeklappt ist, um das Formular übersichtlich zu halten.
- Diese Info-Bereiche dürfen selbst **keine Eingabedaten** erzeugen (rein informativ),
  auch wenn ein direkter Aufruf der Konfigurations-API (nicht über das Frontend)
  erfolgt.
- Die Oberfläche muss vollständig lokalisiert sein, mindestens für **Englisch und
  Deutsch**, inklusive der Info-/Beispieltexte. Beide Sprachversionen müssen
  inhaltlich synchron gehalten werden (gleiche Struktur/Schlüssel).

### 2.7 Installation & Vertrieb

- Verteilung als **HACS-Custom-Repository** (Kategorie "Integration"), alternativ
  manuelles Kopieren des Ordners nach `config/custom_components/`.
- Ein direkter "In Home Assistant öffnen"-Link/Badge für die HACS-Installation.
- Nach Installation: normale Einbindung über Settings → Devices & Services →
  Helpers → "+ Create Helper" → "Template Forecast" (kein YAML nötig).

---

## 3. Nicht-funktionale Anforderungen

- **Keine YAML-Konfiguration nötig** – vollständige Bedienung über die HA-UI.
- **Robustheit:** Fehler in Nutzer-Templates dürfen nie die gesamte Integration oder
  Home Assistant destabilisieren.
- **Nachvollziehbare Fehlermeldungen:** Validierungsfehler werden lokalisiert und am
  richtigen Feld angezeigt, inkl. der eigentlichen Jinja-Fehlermeldung als Kontext.
- **Testbarkeit ohne reale HA-Instanz:** Kernlogik (Config-Flow, Sensorberechnung) muss
  automatisiert und ohne manuellen Klick-Test durch eine echte HA-Installation
  überprüfbar sein.
- **UI-Rendering-Absicherung:** Zusätzlich zur reinen Logik muss überprüfbar sein, dass
  Übersetzungen/Formatierungen (Markdown, Sonderzeichen in Templates) auch tatsächlich
  korrekt im Frontend dargestellt werden, nicht nur syntaktisch korrekt sind.
- **Automatisiertes Releasing:** Versionierung, Changelog und Veröffentlichung neuer
  Versionen erfolgen ohne manuellen Eingriff, ausgelöst durch Commits nach klar
  definierten Regeln.
- **CI-Gate:** Kein Release darf veröffentlicht werden, wenn die automatisierten Tests
  fehlschlagen.

---

## 4. Technische Aspekte (optional beim Neuerstellen)

> Dieser Abschnitt kann beim kompletten Neuaufbau des Projekts ignoriert oder durch
> eine andere technische Lösung ersetzt werden – er beschreibt *wie* aktuell umgesetzt
> wurde, nicht was zwingend erforderlich ist.

### 4.1 Plattform & Aufbau
- Home-Assistant Custom Component (`custom_components/template_forecast`), als
  `integration_type: helper` deklariert (`manifest.json`), damit sie über den
  Standard-Helper-Dialog statt eigener YAML-Konfiguration läuft.
- Zwei Home-Assistant-Konzepte kombiniert:
  - `ConfigFlow`/`OptionsFlowWithReload` (`config_flow.py`) für Erstellung/Bearbeitung.
  - `SensorEntity` + `RestoreEntity` (`sensor.py`) für die eigentliche Entity.
- Zentrale Konstanten/Config-Keys in `const.py`.

### 4.2 Config-Flow-Implementierungsdetails
- Getrennte Schritte: `user` (Name + Modus) → optional `transform_source` (Quell-Entity)
  → `generate`/`transform` (restliche Felder).
- `_LenientTemplateSelector`: umgeht die eingebaute, nicht lokalisierbare
  Syntaxvalidierung von `TemplateSelector`, damit eigene, lokalisierte
  Fehlermeldungen (`_validate_templates`) konsistent in UI und direkten
  API-Aufrufen (Tests) greifen.
- Info-Bereiche pro Template-Feld: `section(..., collapsed=True)` mit einem
  `TemplateSelector({"read_only": True})`-Feld als Träger für ein
  Beispiel-Template (echter, nicht editierbarer CodeMirror-Editor) plus
  `data_description` des Feldes als echtes Markdown (`ha-markdown`). Diese Kombination
  ist der einzige bekannte Weg, echtes Code-Highlighting + Markdown-Doku innerhalb
  eines eingeklappten Abschnitts darzustellen (Section-eigene Beschreibungen rendern
  nur Plain-Text; `ConstantSelector` ignoriert Feld-Label/Helper komplett;
  `BooleanSelector` zeigt immer einen sichtbaren Toggle).
  Frontend und `strip_info_sections()` (serverseitig, doppelte Absicherung) sorgen
  dafür, dass diese reinen Anzeige-Felder nie in die gespeicherten Daten gelangen.
- Übersetzungs-Keys für Felder innerhalb einer Section liegen unter
  `sections.<section_key>.data`/`data_description`, nicht unter dem flachen
  `data`/`data_description` der Step.
- `strings.json`/`translations/{en,de}.json` werden als **ICU MessageFormat**
  geparst (nicht Python `str.format`): Literale `{`/`}` müssen per ICU-Quoting
  (`'...'`) escaped werden, nicht durch Verdoppelung.

### 4.3 Sensor-Berechnungslogik
- Merge von `config_entry.data` und `.options` (Options überschreiben Data) als
  effektive Konfiguration.
- Abhängigkeits-Tracking über `Template.async_render_to_info()` mit Dummy-Variablen,
  um automatisch alle referenzierten Entities zu ermitteln und deren
  Zustandsänderungen zu abonnieren (`async_track_state_change_event`), zusätzlich
  periodischer Timer (`async_track_time_interval`) als Fallback.
- `_try_number()`: gerenderte Template-Strings werden nach Möglichkeit in `int`/`float`
  konvertiert, damit numerische Werte nicht als String im State landen.
- Fehler beim Rendern/Berechnen werden abgefangen und geloggt (`_LOGGER.exception`),
  ohne den State zu invalidieren.

### 4.4 Tests
- **Unit-/Flow-Tests** (`tests/`, `pytest-homeassistant-custom-component`): mocken HA
  komplett, laufen ohne echte Installation. Decken Config-/Options-Flow
  (Generate/Transform, Ablehnung ungültiger/fehlschlagender Templates) und
  Sensor-Berechnung (lineare Rampe, Item-Transformation, automatische
  Neuberechnung, leere Quelle) ab.
- **Translations-Tests** (`tests/test_translations.py`): laden Strings über den
  echten HA-Übersetzungs-Loader, prüfen ICU-Syntax, Markdown-in-Plain-Text-Fallen,
  en/de-Drift und referenzierte-aber-fehlende Keys.
- **Echte Browser-E2E-Tests** (`tests_e2e/`, eigene `pytest.ini`, deaktiviert die
  Mock-/Socket-Blocking-Plugins von `tests/`): bootet eine echte, wegwerfbare
  `hass`-Instanz mit echtem `home-assistant-frontend`, automatisiert Onboarding via
  Playwright, klickt durch Generate- und Transform-Flow, klappt alle Info-Bereiche
  auf und vergleicht den **gerenderten** Text 1:1 (nicht nur die Quell-JSON), inkl.
  Screenshots als Build-Artefakt. Nötig wegen Dingen, die nur ein echter Browser
  zeigt (CodeMirror-Inhalt, Shadow-DOM von `ha-markdown`, HA-Sicherheitsdialog bei
  zufälligem Port, virtualisierte Entity-Picker-Liste).
- Getrennte Requirements-Dateien (`requirements_test.txt` vs. `requirements_e2e.txt`),
  da die E2E-Suite deutlich schwerere Abhängigkeiten (Playwright, Chromium-Download,
  echtes Frontend-Paket) und Laufzeit hat.

### 4.5 CI/CD
- `.github/workflows/test.yml`: mockte Testsuite auf jedem PR.
- `.github/workflows/test-e2e.yml`: Browser-E2E-Suite auf jedem PR (separat, nicht
  Teil des Release-Gates, wegen Laufzeit), lädt Screenshots als Artefakt hoch.
- `.github/workflows/release.yml`: `semantic-release`, ausgelöst durch Pushes nach
  `master`, analysiert Conventional Commits (`fix:` → Patch, `feat:` → Minor,
  `feat!:`/`BREAKING CHANGE:` → Major), bumpt `manifest.json` (`scripts/bump_version.py`),
  aktualisiert `CHANGELOG.md`, taggt, veröffentlicht GitHub Release. Der Release-Job
  hat einen **Test-Gate** (`needs: test`) – kein Release ohne grüne Tests.
- Wichtige, hart erarbeitete Stolperfallen (siehe Projekt-Memory für Details):
  gepinnte `homeassistant`-Version verlangt Python ≥ 3.14.2; `python -m pytest`
  statt bloßem `pytest` nötig, da sonst das Repo-Root nicht auf `sys.path` landet.

### 4.6 Sonstiges
- Versionierte `manifest.json` gemäß HACS/HA-Anforderungen an Custom Integrations.
- `hacs.json` für HACS-Metadaten.
