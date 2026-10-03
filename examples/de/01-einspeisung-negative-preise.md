# Beispiel 1: Einspeisevergütung bei negativen Börsenpreisen

**Modus:** Transform (bestehende Preisprognose umrechnen)

## Ziel

Wer seinen Strom direkt vermarktet oder eine marktpreisabhängige Vergütung
bekommt, bekommt bei negativen Börsenpreisen **kein Geld** für die
Einspeisung (teils muss man sogar zahlen). Die Optimierung soll in diesen
Stunden deshalb nicht einspeisen, sondern Speicher laden, Verbraucher
versorgen oder die Erzeugung abregeln.

Dafür wird ein Sensor erstellt, der aus dem Börsenpreis einen
**Einspeisepreis** ableitet:

- Bei negativem Börsenpreis ist die Einspeisung **0 €/kWh** wert.
- Sonst gilt ein fester Vergütungssatz, der bei niedrigem Börsenpreis
  anteilig gemindert wird. Damit wird ein netzdienliches verhalten der 
  Akkus erreicht.

Eine fertige Prognose-Liste ist dafür nötig, weil HAEO den Preis für jeden
Zeitschritt des Planungshorizonts braucht und nicht nur den aktuellen Wert.

## Wo wirkt er in HAEO

Als **Einspeisepreis (Export Price)** am **Netzanschluss (Grid)**.
Das ist dort, wo normalerweise der Preis für Einspeisung in €/kWh
eingetragen wird. Anstelle eines festen Werts oder eines reinen
Börsenpreis-Sensors wird dieser Sensor ausgewählt.

> Die genauen Feldbezeichnungen können je nach HAEO-Version leicht
> abweichen.

## Helfer-Einstellungen

| Einstellung | Wert |
|---|---|
| Modus | Transform |
| Quell-Entität | `sensor.EPEX_PREIS` |
| Quell-Attribut | `data` |
| Ziel-Attribut | `forecast` |
| Einheit | `€/kWh` |
| Geräteklasse | `monetary` |
| Zustandsklasse | `measurement` |
| Aktualisierungsintervall | 60 min (die Quelle liefert selbst feste Zeitstempel) |

## Verwendete externe Sensoren und Werte

| Platzhalter | Was er darstellt | Einheit | Erwartetes Format |
|---|---|---|---|
| `sensor.EPEX_PREIS` | Börsenstrompreis (Day-Ahead), z. B. aus der Integration *EPEX Spot* | €/kWh | **State:** aktueller Preis als Zahl. **Attribut `data`:** Liste von Einträgen `{start_time, end_time, price_per_kwh}`, Zeitstempel als ISO-8601 mit Zeitzone, z. B. `2026-10-01T00:15:00+02:00` |
| `input_number.EINSPEISEVERGUETUNG_SATZ` | Vergütungssatz, den du für eingespeisten Strom erhältst (Zahlenhelfer, selbst anlegen) | €/kWh | Zahl, z. B. `0.0786` (Box-Modus, Schritt 0,001) |

Das Quellattribut kann auch einen anderen Namen oder andere Schlüssel haben
(z. B. Tibber, aWATTar, Nordpool). Dann müssen `item.price_per_kwh` und
`item.start_time` in den Templates angepasst werden.

## Konstanten im Template

| Konstante | Bedeutung |
|---|---|
| `0` (bei Börsenpreis `< 0`) | Schwelle und Ergebnis: Ab einem Preis unter 0 €/kWh wird die Einspeisung mit 0 bewertet. Wenn du auch bei kleinen positiven Preisen nicht einspeisen willst, erhöhe die Schwelle. |
| `0.20` | Abschlagsfaktor (20 %): Liegt der Börsenpreis unter dem Vergütungssatz, werden 20 % der Differenz („gap") vom Satz abgezogen. Je niedriger der Börsenpreis, desto weniger lohnt die Einspeisung. `0` = reiner fester Satz, `1` = Vergütung folgt voll dem Börsenpreis. |
| `4` (bei `round(4)`) | Rundung auf 4 Nachkommastellen. |
| `0` (bei `float(0)`) | Fallback, falls ein Sensor `unavailable`/`unknown` ist. Hier wird dann mit 0 gerechnet. |

## State-Template

```jinja
{% set strompreis = states('sensor.EPEX_PREIS') | float(0) %}
{% set satz = states('input_number.EINSPEISEVERGUETUNG_SATZ') | float(0) %}
{% set gap = [satz - strompreis, 0] | max %}
{% if strompreis < 0 %}
  {{ 0 }}
{% else %}
  {{ (satz - 0.20 * gap) | round(4) }}
{% endif %}
```

Der State entspricht dem Wert für den aktuellen Zeitpunkt, also derselben
Rechnung wie im Attribut-Template, nur mit dem aktuellen Börsenpreis.

## Attribut-Template

Wird einmal pro Eintrag der Quellliste (`data`) ausgeführt. `item` ist der
jeweilige Eintrag.

```jinja
{% set strompreis = item.price_per_kwh | float(0) %}
{% set satz = states('input_number.EINSPEISEVERGUETUNG_SATZ') | float(0) %}
{% set gap = [satz - strompreis, 0] | max %}
{% if strompreis < 0 %}
  {{ { "time": item.start_time, "value": 0 } }}
{% else %}
  {{ { "time": item.start_time, "value": (satz - 0.20 * gap) | round(4) } }}
{% endif %}
```

Das Ergebnis ist je Eintrag ein Dict mit `time` und `value`. Die übrigen
Felder der Quelle (`start_time`, `end_time`, `price_per_kwh`) bleiben im
Eintrag erhalten.

## Typische Anpassungen

- Quelle wechseln: `sensor.EPEX_PREIS`, Quellattribut und die Schlüssel
  `price_per_kwh` / `start_time` anpassen.
- Netzentgelte oder Steuern einrechnen: im Attribut-Template vom
  `strompreis` einen festen Aufschlag abziehen oder addieren, bevor
  verglichen wird.
