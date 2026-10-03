# Beispiel 4: Ladeleistung der Wallbox begrenzen (abhängig von einem anderen Verbraucher)

**Modus:** Transform (Prognose eines anderen Verbrauchers umrechnen)

## Ziel

Wallbox und ein weiterer großer Verbraucher (im Beispiel eine Klimaanlage)
hängen an **derselben Phase** (L1), deren Absicherung begrenzt ist. Die
Wallbox darf nur so viel Strom ziehen, wie auf der Phase noch frei ist,
sonst löst die Sicherung aus oder das Lastmanagement greift hart ein.

Der Sensor berechnet je Zeitschritt die **maximal mögliche Ladeleistung**:

```
frei [A] = Phasenlimit − Reserve für übrige Grundlast − Strom des anderen Verbrauchers
```

- Ist weniger als der Mindest-Ladestrom (6 A) frei, wird die Leistung auf
  **0** gesetzt (Laden ist dann nicht möglich).
- Sonst wird auf den maximalen Ladestrom (16 A) gedeckelt und in
  Leistung (kW) umgerechnet.

Weil die Prognose des anderen Verbrauchers die Quelle ist, sinkt das Limit
genau in den Stunden, in denen er viel verbraucht (z. B. Klimaanlage
mittags bei Hitze oder Wärmepumpe nachts bei Kälte). 

## Wo wirkt er in HAEO

Als **maximale Ladeleistung (Max. Charge Power, in kW)** im Batterie-Element,
das das E-Auto repräsentiert. Der Sensor wird dort anstelle eines festen
Werts ausgewählt.

> Die genauen Feldbezeichnungen können je nach HAEO-Version leicht
> abweichen.

## Helfer-Einstellungen

| Einstellung | Wert |
|---|---|
| Modus | Transform |
| Quell-Entität | `sensor.VERBRAUCHER_PROGNOSE` |
| Quell-Attribut | `forecast` |
| Ziel-Attribut | `forecast` |
| Einheit | `kW` |
| Geräteklasse | `power` |
| Zustandsklasse | `measurement` |
| Aktualisierungsintervall | 15 min |

## Verwendete externe Sensoren und Werte

| Platzhalter | Was er darstellt | Einheit | Erwartetes Format |
|---|---|---|---|
| `sensor.VERBRAUCHER_PROGNOSE` | Leistungsprognose des anderen Verbrauchers auf derselben Phase | kW | Attribut `forecast`: Liste von Einträgen `{time, value}`, `value` in **kW** (z. B. `0.5591`) |
| `input_number.WALLBOX_PHASENLIMIT` | Maximaler Strom, den die Phase insgesamt tragen darf (Absicherung bzw. Netzanschluss; Zahlenhelfer, selbst anlegen) | A | Zahl, z. B. `25` |
| `input_number.WALLBOX_GRUNDLAST_RESERVE` | Strom, der für alle übrigen, nicht prognostizierten Verbraucher auf der Phase freigehalten wird (Licht, Haushaltsgeräte, …; Zahlenhelfer, selbst anlegen) | A | Zahl, z. B. `4` |

Die Zahlenhelfer machen es möglich, Limit und Reserve im Dashboard zu
ändern, ohne das Template zu bearbeiten.

## Konstanten im Template

| Konstante | Bedeutung |
|---|---|
| `230` | Netzspannung in V (Außenleiter gegen Neutralleiter), um die Leistung des anderen Verbrauchers in Ampere umzurechnen: `A = W / 230`. |
| `6` | Mindest-Ladestrom in A. Unterhalb davon können Wallbox und Auto nicht laden (Norm für AC-Laden). Darunter wird die Leistung auf 0 gesetzt. |
| `16` | Maximaler Ladestrom pro Phase in A (Grenze von Wallbox/Auto, hier ein 11-kW-Setup). |
| `0.69` | kW pro Ampere Ladestrom bei **3-phasigem** Laden: `3 × 230 V / 1000`. Bei 1-phasigem Laden `0.23` verwenden. |
| `25` (bei `float(25)`) | Fallback für das Phasenlimit, falls der Helfer nicht verfügbar ist. |
| `4` (bei `float(4)`) | Fallback für die Reserve, falls der Helfer nicht verfügbar ist. |
| `0` (bei `float(0)`) | Fallback, falls der Wert der Quelle fehlt. |
| `1000` | Umrechnung kW → W. |
| `2` (bei `round(2)`) | Rundung auf 2 Nachkommastellen. |

Hinweis: Weil die Wallbox das Limit **symmetrisch** auf alle Phasen
anwendet, entscheidet die am stärksten belegte Phase (hier L1) über die
Ladeleistung.

## State-Template

```jinja
{{ forecast[0].value }}
```

Der State ist der aktuelle Wert, also der erste Eintrag der berechneten
Prognose (`forecast` ist hier die bereits fertige Ergebnisliste).

## Attribut-Template

Wird einmal pro Eintrag der Quellliste ausgeführt. `value` ist
`item.value`, also die Leistung des anderen Verbrauchers in kW.

```jinja
{% set a = states('input_number.WALLBOX_PHASENLIMIT') | float(25)
         - states('input_number.WALLBOX_GRUNDLAST_RESERVE') | float(4)
         - value | float(0) * 1000 / 230 %}
{{ (0 if a < 6 else ([a, 16] | min) * 0.69) | round(2) }}
```

Das Ergebnis ist je Eintrag eine Zahl in kW. Der Zeitstempel (`time`) wird aus
der Quellliste übernommen.

## Typische Anpassungen

- 1-phasiges Laden: `0.69` durch `0.23` ersetzen.
- Anderer Maximalstrom der Wallbox: `16` anpassen (z. B. `32` für 22 kW).
- Mehrere Verbraucher auf der Phase: in der Quelle eine Summe bilden
  (z. B. ein weiterer Prognose-Sensor) oder die Summe der Werte in
  `value` im Template addieren.
- Zeigt die Quelle Watt statt kW: `* 1000` entfernen.
