# Beispiel 2: Verfügbarkeit des E-Autos (als Ladekosten-Signal)

**Modus:** Generate (Prognose aus Zeitplan und Zustand erzeugen)

Dieses Beispiel gehört zusammen mit
[Beispiel 3: Ziel-Ladezustand](03-ev-ziel-ladezustand.md): Hier wird die
**Verfügbarkeit** des Autos prognostiziert (wann steht es zum Laden bereit?),
in Beispiel 3 das **Ladeverhalten** (auf wie viel und bis wann soll geladen
werden?).

## Ziel

HAEO soll wissen, in welchen Stunden das E-Auto überhaupt zum Laden zur
Verfügung steht: nur wenn es angesteckt ist und zeitlich passt. Die
Verfügbarkeit wird dazu als Preissignal je Stunde ausgedrückt:

- **Negativer Wert** (Bonus): Laden wird belohnt, die Optimierung lädt das
  Auto bevorzugt in diesen Stunden.
- **Hoher positiver Wert**: Laden ist „teuer", die Optimierung vermeidet es.

Ist das Auto nicht angesteckt, ist der Wert immer hoch. Dadurch wird nie
Energie für ein Auto eingeplant, das gar nicht lädt.

Das **Zeitfenster** im Template bildet vor allem **bekannte, regelmäßige
Abwesenheiten** ab (z. B. die Arbeitszeit). Der Sensor „angesteckt" kennt nur
den aktuellen Zustand. Ohne das Fenster würde HAEO für die Stunden, in denen
das Auto erfahrungsgemäß nicht zu Hause ist, trotzdem Ladung einplanen, nur
weil das Auto jetzt gerade angesteckt ist.

Der Wert ist kein echter Strompreis, sondern ein **Steuerungsinstrument**:
Er verschiebt die Lade-Entscheidung in erwünschte Stunden.

## Wo wirkt er in HAEO

Als **Preis für das Laden der Batterie des E-Autos**, im Batterie-Element, das
das Auto repräsentiert (Lade-/Entlade-Kosten, in €/kWh). Der Sensor wird
dort anstelle eines festen Werts ausgewählt.

> Die genauen Feldbezeichnungen können je nach HAEO-Version leicht
> abweichen.

## Helfer-Einstellungen

| Einstellung | Wert |
|---|---|
| Modus | Generate |
| Planungshorizont | 72 Schritte à 60 Minuten (muss zum HAEO-Horizont passen) |
| Ziel-Attribut | `forecast` |
| Einheit | `€/kWh` |
| Geräteklasse | `monetary` |
| Zustandsklasse | `measurement` |
| Aktualisierungsintervall | 60 min |

> Das Template rechnet mit **Stundenschritten**. Bei einer anderen
> Schrittweite muss die Stundenberechnung angepasst werden.

## Verwendete externe Sensoren und Werte

| Platzhalter | Was er darstellt | Einheit | Erwartetes Format |
|---|---|---|---|
| `binary_sensor.EV_ANGESTECKT` | Ist das Ladekabel am Auto bzw. an der Wallbox angesteckt? | – | `on` / `off`. `unavailable`/`unknown` wird wie „nicht angesteckt" behandelt (`bool(false)`) |

Außerdem wird die aktuelle Uhrzeit verwendet (`now()`, in der lokalen
Zeitzone von Home Assistant). `index` ist der Schrittindex (0 = jetzt,
1 = in einer Stunde, …).

## Konstanten im Template

| Konstante | Bedeutung |
|---|---|
| `-0.06` | Bonus in €/kWh, wenn das Laden erwünscht ist (Auto angesteckt und Uhrzeit im Ladefenster). Je stärker negativ, desto stärker wird geladen. |
| `0.26` | „Sperrpreis" in €/kWh: Laden ist unerwünscht (Auto nicht angesteckt oder außerhalb des Ladefensters). Sinnvoll etwa auf Höhe des Netzbezugspreises oder darüber, damit HAEO nicht aus dem Netz nachlädt. Die `0.26` liegen aber unter den Kosten für den Netzbezug. Damit kann auch mit dynamischen Netzengelten gearbeitet werden. |
| `7` und `12` | Grenzen der Stunden (lokale Uhrzeit), in denen das Auto **voraussichtlich nicht verfügbar** ist, z. B. wegen der Arbeitszeit. Hier: Stunden 7 bis einschließlich 12 sind gesperrt, Laden ist vor 7 Uhr (Nacht) und ab 13 Uhr erwünscht. An die eigenen regelmäßigen Abwesenheiten anpassen. Nebeneffekt: Die Optimierung füllt in dieser Zeit stattdessen andere Akkus stärker, um das Auto danach daraus laden zu können. |
| `24` | Stunden pro Tag, damit der Stundenindex nach Mitternacht wieder bei 0 beginnt. |
| `false` (bei `bool(false)`) | Fallback für einen nicht verfügbaren Sensor. |

## State-Template

```jinja
{% if states('binary_sensor.EV_ANGESTECKT') | bool(false) %}
  -0.06
{% else %}
  0.26
{% endif %}
```

Der State zeigt den aktuell gültigen Wert an, hier ohne Zeitfenster-Prüfung. Er
dient nur der Anzeige. HAEO liest die Werte aus dem Attribut.

## Attribut-Template

Wird für jeden Planungsschritt einmal ausgeführt. `index` ist der Schritt.

```jinja
{% set hourOfDay = (now().hour + index) % 24 %}
{% if states('binary_sensor.EV_ANGESTECKT') | bool(false) and ((hourOfDay < 7) or (hourOfDay > 12)) %}
  -0.06
{% else %}
  0.26
{% endif %}
```

Das Ergebnis ist je Schritt eine einzelne Zahl. Der Zeitstempel (`time`)
wird automatisch ergänzt.

## Typische Anpassungen

- Abwesenheitsfenster ändern: `7` und `12` austauschen, z. B. auf die
  eigene Arbeitszeit. Für ein Fenster, das über Mitternacht geht oder
  umgekehrt nur ein Ladefenster erlauben soll (z. B. nur nachts 22–6 Uhr),
  die Bedingung umdrehen: `hourOfDay >= 22 or hourOfDay < 6`.
- Unterschiedliche Zeiten an Werktagen und am Wochenende: zusätzlich
  `(now() + timedelta(hours=index)).weekday() < 5` prüfen.
- Kein Zeitfenster gewünscht: den Teil nach `and` entfernen. Dann wird
  immer geladen, sobald das Auto angesteckt ist, und zwar zu den
  günstigsten Zeiten laut Optimierung.
