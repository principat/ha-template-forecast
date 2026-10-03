# Beispiel 3: Ziel-Ladezustand des E-Autos zu einer Uhrzeit (Deadline)

**Modus:** Generate (Prognose aus Zeitplan und Einstellungen erzeugen)

Dieses Beispiel gehört zusammen mit
[Beispiel 2: Verfügbarkeit](02-ev-ladekosten.md): Dort wird prognostiziert,
**wann das Auto verfügbar ist**, hier das **Ladeverhalten**: auf wie viel und
bis wann geladen werden soll.

## Ziel

Das Auto soll zu einer bestimmten Uhrzeit (z. B. morgens um 6 Uhr, wenn
man losfährt) auf einen gewünschten Ladezustand geladen sein. Zu allen
anderen Zeiten reicht ein niedriger Grundwert.

Der Sensor liefert dafür für jede Stunde des Horizonts einen
Ziel-Ladezustand in Prozent:

- zur eingestellten Ziel-Stunde: der gewünschte Ziel-Ladezustand,
- sonst: ein Grundwert (Basis).

Ziel-Stunde und Ziel-Ladezustand lassen sich z.B. in einem Dashboard über zwei
Zahlenhelfer ändern, ohne das Template anzufassen.

> **Warnung: Der Zielwert ist keine Garantie.**
> HAEO behandelt den Ziel-Ladezustand nicht als harte Grenze. Das Unterschreiten
> des Werts verursacht in der Optimierung nur **Kosten**, die gegen alle
> anderen Kosten und Erlöse (Strompreise, Einspeisung, Verschleiß usw.)
> abgewogen werden. HAEO entscheidet deshalb weiterhin selbst, ob das Auto
> wirklich auf den Zielwert geladen wird. Ist das Unterschreiten in einer
> Situation günstiger, wird es in Kauf genommen.
>
> Wer sich darauf verlassen muss, dass das Auto zur Zielzeit voll genug ist
> (z. B. für die Fahrt zur Arbeit), sollte **in der Wallbox-Steuerung eine
> zusätzliche Sicherung** einbauen. Das kann etwa eine Automation sein, die
> unabhängig von HAEO mit voller Leistung lädt, wenn der Ladezustand
> rechtzeitig vor der Ziel-Stunde noch zu niedrig ist.

## Wo wirkt er in HAEO

Als **zeitabhängiger Ziel-/Mindest-Ladezustand (SoC, in %)** im
Batterie-Element, das das E-Auto repräsentiert. Der Sensor wird dort anstelle
eines festen Werts ausgewählt. HAEO plant dann das Laden so, dass der Wert
zur jeweiligen Stunde erreicht ist.

> Die genauen Feldbezeichnungen können je nach HAEO-Version leicht
> abweichen.

## Helfer-Einstellungen

| Einstellung | Wert |
|---|---|
| Modus | Generate |
| Planungshorizont | 72 Schritte à 60 Minuten (muss zum HAEO-Horizont passen) |
| Ziel-Attribut | `forecast` |
| Einheit | `%` |
| Geräteklasse | leer |
| Zustandsklasse | `measurement` |
| Aktualisierungsintervall | 60 min |

> Das Template rechnet mit **Stundenschritten**, die auf die volle Stunde
> ausgerichtet sind. Bei einer anderen Schrittweite muss `timedelta(hours=index)`
> angepasst werden.

## Verwendete externe Sensoren und Werte

| Platzhalter | Was er darstellt | Einheit | Erwartetes Format |
|---|---|---|---|
| `input_number.EV_ZIEL_STUNDE` | Uhrzeit, zu der das Auto geladen sein soll (Zahlenhelfer, selbst anlegen) | Stunde | Ganzzahl 0–23, lokale Zeit, z. B. `6` |
| `input_number.EV_ZIEL_LADEZUSTAND` | Gewünschter Ladezustand zu dieser Stunde (Zahlenhelfer, selbst anlegen) | % | Zahl 0–100, z. B. `60` (Schritt 5) |

Außerdem wird die aktuelle Uhrzeit verwendet (`now()`, lokale Zeitzone von
Home Assistant).

## Konstanten im Template

| Konstante | Bedeutung |
|---|---|
| `baseline = 40` | Grundwert in %, der zu allen Stunden außer der Ziel-Stunde gilt. Das ist der Ladezustand, der als Untergrenze immer gehalten werden soll (Reichweitenreserve). `0` = keine Reserve. |
| `6` (bei `int(6)`) | Fallback für die Ziel-Stunde, falls der Zahlenhelfer nicht verfügbar ist. |
| `80` (bei `float(80)`) | Fallback für den Ziel-Ladezustand, falls der Zahlenhelfer nicht verfügbar ist. |
| `minute=0, second=0, microsecond=0` | Rundet „jetzt" auf die volle Stunde ab, damit die Zeitstempel zu den Stundenwerten passen. |

## State-Template

```jinja
{% set target_hour = states('input_number.EV_ZIEL_STUNDE') | int(6) %}
{% set target_soc = states('input_number.EV_ZIEL_LADEZUSTAND') | float(80) %}
{% set baseline = 40 %}
{{ target_soc if now().hour == target_hour else baseline }}
```

Der State zeigt den aktuell gültigen Wert (Ziel oder Grundwert).

## Attribut-Template

Wird für jeden Planungsschritt einmal ausgeführt. `index` ist der Schritt.

```jinja
{% set base = now().replace(minute=0, second=0, microsecond=0) %}
{% set target = base + timedelta(hours=index) %}
{% set target_hour = states('input_number.EV_ZIEL_STUNDE') | int(6) %}
{% set target_soc = states('input_number.EV_ZIEL_LADEZUSTAND') | float(80) %}
{% set baseline = 40 %}
{{ {
   "time": target.isoformat(),
   "value": target_soc if target.hour == target_hour else baseline
   } }}
```

Das Template gibt ein Dict mit `time` und `value` zurück. Der Zeitstempel
wird hier selbst gesetzt, weil er an der lokalen Stunde ausgerichtet ist
(die Ziel-Stunde bezieht sich auf die lokale Uhrzeit, nicht auf UTC).

## Typische Anpassungen

- Mehrere Termine (z. B. Werktage anders als Wochenende): im Attribut-Template
  zusätzlich `target.weekday()` prüfen (0 = Montag … 6 = Sonntag).
- Ziel nur, wenn das Auto angesteckt ist: zusätzlich
  `states('binary_sensor.EV_ANGESTECKT') | bool(false)` abfragen und sonst
  `0` liefern (siehe [Beispiel 2](02-ev-ladekosten.md)).
