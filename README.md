# Template Forecast (Home Assistant Helper)

Ein HACS-Custom-Integration, die Forecast-Sensoren aus Jinja2-Templates erzeugt –
als "Helfer" über die normale UI (Einstellungen → Geräte & Dienste → Helfer → Helfer erstellen).

Zwei Modi:

- **Generate**: du gibst einen Planungshorizont (Anzahl Schritte + Schrittweite) an. Das
  Attribut-Template wird für jeden Schritt einmal ausgewertet und ergibt eine `forecast`-Liste
  (Standardname konfigurierbar).
- **Transform**: du wählst eine bestehende Entität, deren Listen-Attribut (z. B. `forecast`)
  Schritt für Schritt durch dein Template gejagt wird (Zeitstempel bleiben erhalten, nur der
  Wert wird transformiert).

In beiden Modi ist zusätzlich ein **State-Template** Pflicht, das unabhängig vom Attribut-Template
gerendert wird und Zugriff auf das fertige Forecast-Ergebnis hat (Variable `forecast`).

## Tests

```bash
pip install -r requirements_test.txt
pytest
```

8 Tests decken Config-Flow (Generate/Transform/Options, inkl. Ablehnung ungültiger
Templates) und die Sensor-Berechnungslogik (lineare Rampe, Element-Transformation,
automatisches Neuberechnen bei Quell-Update, leere Quelle) ab.

## Installation

1. Als Custom Repository in HACS hinzufügen (Kategorie "Integration") oder den Ordner
   `custom_components/template_forecast` manuell nach `config/custom_components/` kopieren.
2. Home Assistant neu starten.
3. Einstellungen → Geräte & Dienste → Helfer → "+ Helfer erstellen" → "Template Forecast".

## Bearbeiten

Bereits erstellte Helfer lassen sich jederzeit über die drei Punkte am Helfer → "Konfigurieren"
erneut öffnen. Der Modus (Generate/Transform) ist nach dem Anlegen fix, alle übrigen Felder
(Templates, Horizont, Update-Intervall, Zielattribut, Quelle) sind änderbar.

## Template-Variablen

### Generate-Modus, Attribut-Template
- `index` – 0-basierter Schrittindex
- `horizon` – Gesamtzahl der Schritte
- `forecast_time` – Zeitpunkt dieses Schritts (datetime, UTC)

### Transform-Modus, Attribut-Template
- `index` – Position in der Quell-Liste
- `item` – das komplette Original-Element (dict) aus dem Quellattribut
- `value` – `item.value`, falls vorhanden (Convenience)
- `orig_datetime` – `item.datetime`, falls vorhanden (Convenience)

### State-Template (beide Modi)
- `forecast` – die bereits berechnete Ergebnis-Liste (Liste von `{datetime, value}`)
- zusätzlich im Transform-Modus: `source` (State der Quell-Entität), `source_forecast`
  (Original-Liste vor der Transformation)
- alle normalen Jinja-Funktionen (`states()`, `state_attr()`, `now()`, …) stehen wie gewohnt
  zur Verfügung.

## Standard-Sensor-Eigenschaften

Wie beim eingebauten Template-Sensor-Helfer lassen sich zusätzlich pflegen (alle optional):

- **Einheit** (`unit_of_measurement`)
- **Geräteklasse** (`device_class`, Dropdown mit allen gültigen `SensorDeviceClass`-Werten)
- **Statusklasse** (`state_class`, `measurement` / `total` / `total_increasing`)
- **Icon** (Icon-Picker, z. B. `mdi:currency-eur`)

Diese Felder wirken sich nur auf den State/die Darstellung der Entität aus, nicht auf die
Berechnung – für die einzelnen Forecast-Werte im Attribut gibt es (bewusst, analog zu den
meisten Forecast-Konventionen) keine separate Einheit pro Listenelement.
