# Beispiel 5: Solar-Ladeverzögerung (früh laden, nicht trödeln)

**Modus:** Generate (Prognose aus mehreren PV-Prognosen erzeugen)

## Ziel

Der Speicher soll möglichst **früh am Tag aus der Sonne geladen** werden, nicht
erst am späten Nachmittag. Ohne Zusatzsignal ist es für die Optimierung
gleichgültig, ob sie die Sonnenenergie um 10 Uhr oder um 15 Uhr in den
Speicher legt. Dann ist der Speicher bei plötzlicher Bewölkung am Nachmittag
oft nicht voll.

Der Sensor erzeugt dafür einen **Kostenverlauf, der ab Sonnenaufgang der PV-Anlage
stündlich ansteigt**: Laden kurz nach PV-Start ist leicht belohnt (negativ),
je später, desto „teurer", bis zu einer Obergrenze. Die Optimierung lädt
dadurch bevorzugt zu Beginn des Sonnenfensters.

Wie bei den E-Auto-Beispielen ist der Wert **kein echter Preis**, sondern ein
Steuerungsinstrument mit kleinen Beträgen. Er soll nur entscheiden, wenn
sonst alles gleichwertig wäre.

## Wo wirkt er in HAEO

Als **zusätzlicher Preis/Kostenterm für das Laden der Hausbatterie** (in
€/kWh), im Batterie-Element bzw. in einer Policy, die das Laden bewertet. Der
Sensor wird dort anstelle eines festen Werts ausgewählt.

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

> Das Template rechnet mit **Stundenschritten** (`timedelta(hours=index)`).
> Bei einer anderen Schrittweite muss das angepasst werden.

## Verwendete externe Sensoren und Werte

| Platzhalter | Was er darstellt | Einheit | Erwartetes Format |
|---|---|---|---|
| `sensor.PV_ANLAGE_1`, `sensor.PV_ANLAGE_2`, … | **Ausgabesensoren von HAEO** je Solar-Element (Entität „Power“ des jeweiligen Solar-Elements, z. B. `sensor.solar_dach_sud_power`). Beliebig viele, in der Liste `solar_sensors` eintragen | kW | Attribut `forecast`: Liste von Einträgen `{time, value}`, `value` in **kW**, z. B. `0.096` |

Es sind also nicht die Eingangs-Prognosen (z. B. von Forecast.Solar), sondern
die **von HAEO berechnete, optimierte PV-Leistung** je Anlage. Zwei
Konsequenzen:

- Der Sensor hängt vom Ergebnis der letzten Optimierung ab und wirkt über
  das Laden der Batterie wieder auf die nächste zurück. Das ist hier gewollt
  und unkritisch, weil die Beträge klein sind.
- Wird PV abgeregelt (z. B. bei negativen Preisen), sinkt die optimierte
  Leistung und damit evtl. unter die Schwelle. Der „PV-Start“ kann sich
  dann verschieben. Wenn das stört, stattdessen die Prognosesensoren
  verwenden, die auch als Eingang für die Solar-Elemente in HAEO dienen.

Wichtig: Alle Sensoren müssen **dieselben Zeitstützstellen und dieselbe
Länge** in `forecast` haben. Das Template addiert die Einträge gleicher
Position und nimmt die Zeitstempel der ersten Anlage. HAEO-Ausgabesensoren
erfüllen das, da sie auf demselben Optimierungshorizont beruhen.

## Konstanten im Template

| Konstante | Bedeutung |
|---|---|
| `threshold = 0.1` | Schwelle in kW für die **summierte** PV-Leistung. Erst darüber gilt es als „PV läuft"; darunter ist es Nacht/Dämmerung. Verhindert, dass minimaler Dämmerungsstrom als Sonnenaufgang zählt. |
| `base = -0.005` | Startwert in €/kWh direkt bei PV-Start (leichter Bonus fürs Laden) und Wert in der Nacht, wenn kein PV-Start in der Prognose gefunden wird. |
| `rate = 0.003` | Anstieg in €/kWh **pro Stunde** seit PV-Start. Je höher, desto stärker wird frühes Laden bevorzugt. |
| `max_ramp = 0.02` | Obergrenze des Anstiegs in €/kWh. Der Wert steigt also höchstens auf `base + max_ramp` (hier `0.015`). So bleibt der Einfluss klein gegenüber echten Preisen. |
| `3600` | Sekunden pro Stunde, nur Umrechnung. |
| `4` (bei `round(4)`) | Rundung auf 4 Nachkommastellen. |

## State-Template

```jinja
{% set solar_sensors = [
    'sensor.PV_ANLAGE_1', 'sensor.PV_ANLAGE_2', 'sensor.PV_ANLAGE_3'
  ] %}
{% set threshold = 0.1 %}
{% set base = -0.005 %}
{% set rate = 0.003 %}
{% set max_ramp = 0.02 %}
{% set forecasts = solar_sensors | map('state_attr', 'forecast') | list %}
{% set ns = namespace(pv_starts=[], was_dark=true) %}
{% for i in range(forecasts[0] | length) %}
  {% set total = forecasts | map(attribute=i) | map(attribute='value') | sum %}
  {% if ns.was_dark and total > threshold %}
    {% set ns.pv_starts = ns.pv_starts + [forecasts[0][i].time] %}
  {% endif %}
  {% set ns.was_dark = total <= threshold %}
{% endfor %}
{% set target = now() %}
{% set past = ns.pv_starts | select('le', target) | list %}
{% if past | length == 0 %}
  {{ base }}
{% else %}
  {% set last_start = past[-1] %}
  {% set hours_since = ((target - last_start).total_seconds() / 3600) %}
  {{ (base + ([hours_since * rate, max_ramp] | min)) | round(4) }}
{% endif %}
```

Der State ist derselbe Verlauf, ausgewertet für „jetzt" (`target = now()`).

## Attribut-Template

Wird für jeden Planungsschritt einmal ausgeführt. `index` ist der Schritt.
Es unterscheidet sich vom State-Template nur im Zielzeitpunkt.

```jinja
{% set solar_sensors = [
    'sensor.PV_ANLAGE_1', 'sensor.PV_ANLAGE_2', 'sensor.PV_ANLAGE_3'
  ] %}
{% set threshold = 0.1 %}
{% set base = -0.005 %}
{% set rate = 0.003 %}
{% set max_ramp = 0.02 %}
{% set forecasts = solar_sensors | map('state_attr', 'forecast') | list %}
{% set ns = namespace(pv_starts=[], was_dark=true) %}
{% for i in range(forecasts[0] | length) %}
  {% set total = forecasts | map(attribute=i) | map(attribute='value') | sum %}
  {% if ns.was_dark and total > threshold %}
    {% set ns.pv_starts = ns.pv_starts + [forecasts[0][i].time] %}
  {% endif %}
  {% set ns.was_dark = total <= threshold %}
{% endfor %}
{% set target = now() + timedelta(hours=index) %}
{% set past = ns.pv_starts | select('le', target) | list %}
{% if past | length == 0 %}
  {{ base }}
{% else %}
  {% set last_start = past[-1] %}
  {% set hours_since = ((target - last_start).total_seconds() / 3600) %}
  {{ (base + ([hours_since * rate, max_ramp] | min)) | round(4) }}
{% endif %}
```

Ablauf: Zuerst werden aus der Summe aller PV-Prognosen die **PV-Starts**
bestimmt (Übergang von „unter Schwelle" zu „über Schwelle"). Dann wird für den
Zielzeitpunkt der letzte PV-Start davor gesucht und die Zeit seitdem in den
Anstieg umgerechnet.

## Typische Anpassungen

- Weitere PV-Anlagen: einfach in `solar_sensors` ergänzen (in beiden
  Templates).
- Stärkeres oder schwächeres Drängen auf frühes Laden: `rate` und
  `max_ramp` anpassen.
- Wird der Sensor mitten am Tag zum ersten Mal ausgewertet, beginnt die
  Prognose bereits im „Sonnenfenster". Der erste Eintrag zählt dann als PV-Start,
  der Anstieg beginnt also ab „jetzt" und nicht ab dem echten Sonnenaufgang.
  Für die Optimierung ist das in der Praxis unkritisch.
