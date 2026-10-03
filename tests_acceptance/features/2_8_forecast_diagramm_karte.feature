# language: de
# REQ 2.8 — docs/REQUIREMENTS.md Abschnitt 2.8
#
# Geprüft wird die plattformunabhängige Logik der Karte (Vorbelegung, Abbildung zwischen Editor
# und gespeicherter Konfiguration, Aufbau der Linien) über card_driver.py. Das Aussehen von
# Diagramm und Editor in einem echten Home-Assistant-Frontend prüft tests_e2e/.
@REQ-2.8
Funktionalität: Forecast-Diagramm-Karte

  Als Nutzer möchte ich Forecast-Sensoren und andere Entitäten mit einer Liste
  von Zeit/Wert-Einträgen als Zeitreihe in einem Dashboard darstellen, die Karte
  ohne YAML im Editor einrichten und jederzeit nachträglich ändern können.

  Grundlage:
    Angenommen eine Entität "sensor.preis" mit der Einheit "€/kWh" und dem Listenattribut "forecast" mit Inhalt:
      | time                      | value | outdoor_temp |
      | 2026-10-02T10:00:00+00:00 | 0.10  | 10           |
      | 2026-10-02T11:00:00+00:00 | 0.20  | 11           |
      | 2026-10-02T12:00:00+00:00 | 0.30  | 12           |
    Und eine Entität "sensor.epex" mit der Einheit "€/kWh" und dem Listenattribut "data" mit Inhalt:
      | start_time                | end_time                  | price_per_kwh |
      | 2026-10-02T10:00:00+00:00 | 2026-10-02T10:15:00+00:00 | 0.15          |
      | 2026-10-02T10:15:00+00:00 | 2026-10-02T10:30:00+00:00 | 0.16          |
    Und eine Entität "sensor.leistung" mit der Einheit "kW" und dem Listenattribut "forecast" mit Inhalt:
      | time                      | value |
      | 2026-10-02T10:00:00+00:00 | 3     |
      | 2026-10-02T11:00:00+00:00 | 4     |
    Und eine Entität "sensor.luecke" mit dem Listenattribut "forecast" mit Inhalt:
      | time                      | value |
      | 2026-10-02T10:00:00+00:00 | 1     |
      | 2026-10-02T11:00:00+00:00 | n/a   |
      | 2026-10-02T12:00:00+00:00 | 3     |

  Szenario: Nach der Auswahl einer Entität sind Attribut, Zeit- und Wertefeld vorbelegt
    Wenn im Karten-Editor die Entität "sensor.preis" gewählt wird
    Dann sind im Karten-Editor das Listen-Attribut "forecast", das Zeitfeld "time" und das Wertefeld "value" vorbelegt

  Szenario: Bei anderem Aufbau der Liste wird passend vorbelegt
    Wenn im Karten-Editor die Entität "sensor.epex" gewählt wird
    Dann sind im Karten-Editor das Listen-Attribut "data", das Zeitfeld "start_time" und das Wertefeld "price_per_kwh" vorbelegt

  Szenario: Weitere Wertefelder derselben Entität werden angeboten und als eigene Linie gezeichnet
    Wenn im Karten-Editor die Entität "sensor.preis" gewählt wird
    Dann bietet der Karten-Editor als weitere Wertefelder "outdoor_temp" an
    Und zeigt das Diagramm 1 Linie
    Wenn zusätzlich das Wertefeld "outdoor_temp" gewählt wird
    Dann zeigt das Diagramm 2 Linien

  Szenario: Skalierungsfaktor und Offset wirken auf die gezeichneten Werte
    Wenn im Karten-Editor die Entität "sensor.preis" gewählt wird
    Und der Skalierungsfaktor des Feldes "value" auf 100 gesetzt wird
    Und der Offset des Feldes "value" auf 5 gesetzt wird
    Dann zeigt die Linie "sensor.preis" an Position 2 den Wert 25

  Szenario: Name und Farbe einer Linie lassen sich anpassen
    Wenn im Karten-Editor die Entität "sensor.preis" gewählt wird
    Und der Name des Feldes "value" auf "Strompreis" gesetzt wird
    Und die Farbe des Feldes "value" auf "#123456" gesetzt wird
    Dann hat die Linie "Strompreis" die Farbe "#123456"

  Szenario: Eine gespeicherte Karte wird im Editor unverändert angezeigt und kann jederzeit weiter bearbeitet werden
    Angenommen eine gespeicherte Karte mit der Entität "sensor.preis", dem Wertefeld "value", dem Skalierungsfaktor 10 und dem Namen "Preis"
    Wenn der Karten-Editor mit der gespeicherten Konfiguration geöffnet wird
    Dann zeigt der Karten-Editor für das Feld "value" den Skalierungsfaktor 10 und den Namen "Preis"
    Und ist die gespeicherte Konfiguration der Karte unverändert

  Szenario: Eine Änderung im Detailbereich lässt die übrigen Einstellungen unverändert
    Angenommen eine gespeicherte Karte mit der Entität "sensor.preis" und den Wertefeldern "value" mit Skalierungsfaktor 10 und "outdoor_temp" mit Offset 5
    Wenn der Name des Feldes "value" auf "Preis" gesetzt wird
    Dann bleibt für das Feld "value" der Skalierungsfaktor 10 gespeichert
    Und bleibt für das Feld "outdoor_temp" der Offset 5 gespeichert

  Szenario: Beim Wechsel der Entität wird neu vorbelegt
    Angenommen im Karten-Editor ist die Entität "sensor.preis" gewählt
    Wenn im Karten-Editor die Entität der ersten Quelle auf "sensor.epex" gewechselt wird
    Dann sind im Karten-Editor das Listen-Attribut "data", das Zeitfeld "start_time" und das Wertefeld "price_per_kwh" vorbelegt
    Und enthält die Konfiguration der Quelle nur das Wertefeld "price_per_kwh"

  Szenario: Weitere Entitäten lassen sich hinzufügen und umsortieren
    Angenommen im Karten-Editor ist die Entität "sensor.preis" gewählt
    Wenn im Karten-Editor die weitere Entität "sensor.leistung" hinzugefügt wird
    Dann zeigt das Diagramm 2 Linien
    Und lautet die Reihenfolge der Linien "sensor.preis, sensor.leistung"
    Wenn die Quelle 2 nach oben verschoben wird
    Dann lautet die Reihenfolge der Linien "sensor.leistung, sensor.preis"

  Szenario: Unterschiedliche Einheiten liegen auf getrennten Y-Achsen
    Angenommen im Karten-Editor ist die Entität "sensor.preis" gewählt
    Wenn im Karten-Editor die weitere Entität "sensor.leistung" hinzugefügt wird
    Dann liegt die Linie "sensor.preis" auf der linken Y-Achse
    Und liegt die Linie "sensor.leistung" auf der rechten Y-Achse

  Szenario: Eine fehlende Entität lässt die übrigen Linien bestehen
    Angenommen im Karten-Editor ist die Entität "sensor.preis" gewählt
    Wenn im Karten-Editor die weitere Entität "sensor.gibt_es_nicht" hinzugefügt wird
    Dann zeigt das Diagramm 1 Linie
    Und meldet das Diagramm für "sensor.gibt_es_nicht" den Hinweis "entity_missing"

  Szenario: Nicht numerische Werte werden übersprungen
    Wenn im Karten-Editor die Entität "sensor.luecke" gewählt wird
    Dann hat die Linie "sensor.luecke" 2 Punkte

  Szenario: Der Zeitbereich "ab jetzt" beginnt beim aktuell gültigen Eintrag
    Angenommen die Karte ist auf den Zeitbereich "from_now" eingestellt
    Und der aktuelle Zeitpunkt ist 2026-10-02T11:30:00+00:00
    Wenn im Karten-Editor die Entität "sensor.preis" gewählt wird
    Dann hat die Linie "sensor.preis" 2 Punkte
    Und zeigt die Linie "sensor.preis" an Position 1 den Wert 0.2
