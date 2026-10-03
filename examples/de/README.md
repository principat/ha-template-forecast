# Beispiele

Praxisbeispiele für die Nutzung von Template Forecast zusammen mit
[HAEO](https://haeo.io) (Home Assistant Energy Optimizer). Sie stammen aus einer
laufenden Installation und lassen sich mit kleinen Anpassungen übernehmen:
Platzhalter wie `sensor.EPEX_PREIS` durch eigene Entitäten ersetzen,
Konstanten prüfen, fertig.

[English version](../en/README.md)

## Übersicht

| # | Anwendungsfall | Modus | Wirkt in HAEO als |
|---|---|---|---|
| 1 | [Einspeisung bei negativen Börsenpreisen deaktivieren](01-einspeisung-negative-preise.md) | Transform | Einspeisepreis am Netzanschluss |
| 2 | [E-Auto: Verfügbarkeit (als Ladekosten-Signal)](02-ev-ladekosten.md) | Generate | Ladepreis der E-Auto-Batterie |
| 3 | [E-Auto: Ladeverhalten (Ziel-Ladezustand bis zur Uhrzeit)](03-ev-ziel-ladezustand.md) | Generate | Ziel-/Mindest-SoC der E-Auto-Batterie |
| 4 | [Wallbox-Ladeleistung durch anderen Verbraucher begrenzen](04-wallbox-leistungsbegrenzung.md) | Transform | Maximale Ladeleistung der E-Auto-Batterie |
| 5 | [Solar-Ladeverzögerung: Speicher früh am Tag laden](05-solar-ladeverzoegerung.md) | Generate | Zusatzkosten für das Laden der Hausbatterie |

Die Beispiele 2 und 3 gehören zusammen und steuern das Laden des E-Autos
gemeinsam: 2 prognostiziert die **Verfügbarkeit** des Autos, 3 das
**Ladeverhalten** (auf wie viel und bis wann geladen werden soll).

## Aufbau der Beispiele

Jede Datei ist gleich aufgebaut:

1. **Ziel**: warum der Sensor erstellt wurde
2. **Wo wirkt er in HAEO**
3. **Helfer-Einstellungen**: Modus, Horizont, Einheit usw.
4. **Verwendete externe Sensoren und Werte**: was sie darstellen, Einheit,
   erwartetes Format
5. **Konstanten im Template**: was feste Zahlen bedeuten (reine
   Umrechnungsfaktoren wie 1000 oder 60 ausgenommen)
6. **State-Template** mit Platzhaltern
7. **Attribut-Template** mit Platzhaltern

## So übernimmst du ein Beispiel

1. Benötigte Zahlen-/Schalter-Helfer anlegen
   (Einstellungen → Geräte & Dienste → Helfer), falls im Beispiel genannt.
2. Einstellungen → Geräte & Dienste → Helfer → „Helfer erstellen" →
   **Template Forecast**, Modus laut Beispiel wählen.
3. Platzhalter in beiden Templates durch deine Entitäten ersetzen und die
   Konstanten an deine Anlage anpassen.
4. Einheit, Geräteklasse und Zustandsklasse wie im Beispiel setzen.
5. Den erzeugten Sensor in HAEO an der genannten Stelle auswählen.
6. Im Entwicklerwerkzeug den Sensor prüfen: Der State muss plausibel sein, das
   Attribut `forecast` eine Liste aus `time` und `value`.

## Hinweise

- **Horizont:** Anzahl Schritte × Schrittweite sollte dem HAEO-Horizont
  entsprechen (in den Beispielen 72 × 60 min).
- **Zeitzone:** `now()` liefert lokale Zeit. Die Uhrzeit-Logik der
  Beispiele 2 und 3 bezieht sich daher auf deine lokale Uhrzeit.
- **Fallbacks:** `| float(0)`, `| bool(false)` und ähnliche Angaben verhindern
  Fehler, wenn ein Sensor kurzzeitig `unavailable` ist. Sie sollten
  beibehalten werden.

## Eigenes Beispiel teilen

Du hast eine nützliche Konfiguration? Eröffne ein Issue mit der
[Vorlage „Example"](https://github.com/principat/ha-template-forecast/issues/new?template=example.yml).
