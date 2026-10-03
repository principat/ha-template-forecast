# language: de
# REQ 2.4 — docs/REQUIREMENTS.md Abschnitt 2.4
@REQ-2.4
Funktionalität: Automatische Neuberechnung des Forecast-Sensors

  Als Nutzer eines Template-Forecast-Helpers möchte ich, dass sich der Sensor
  automatisch neu berechnet, wenn sich referenzierte Daten ändern oder Zeit
  vergeht, ohne dass ich manuell eingreifen muss - und dass Fehler dabei nie
  zum Absturz des Helpers führen.

  Szenario: Neuberechnung bei Zustandsänderung einer referenzierten Entity
    Angenommen eine Entity "input_number.aufschlag" mit Zustand "0"
    Und ein Generate-Helper "Preis-Forecast" mit Attribut-Template "{{ index + states('input_number.aufschlag') | float }}"
    Wenn sich der Zustand von "input_number.aufschlag" auf "5" ändert
    Dann hat der Eintrag mit Index 0 im Forecast von "Preis-Forecast" den Wert "5.0"

  Szenario: Neuberechnung im Transform-Modus bei Änderung der Quell-Entity
    Angenommen eine Quell-Entity "sensor.roh_forecast" mit Attribut "forecast" und Inhalt:
      | value |
      | 10    |
    Und ein Transform-Helper "Verdoppelt2" mit Quell-Entity "sensor.roh_forecast", Quell-Attribut "forecast" und Attribut-Template "{{ value * 2 }}"
    Wenn das Attribut "forecast" von "sensor.roh_forecast" geändert wird auf:
      | value |
      | 100   |
    Dann enthält der Forecast von "Verdoppelt2" genau einen Eintrag mit Wert "200"

  Szenario: Der Zustand bleibt bis zum nächsten Neustart erhalten
    Angenommen ein Generate-Helper "Ueberlebt-Neustart" mit Attribut-Template "{{ 42 }}"
    Und der Sensor "Ueberlebt-Neustart" hat den Zustand "42"
    Wenn Home Assistant neu gestartet wird, während "Ueberlebt-Neustart" existiert
    Dann hat der Sensor "Ueberlebt-Neustart" den Zustand "42"

  Szenario: Eine leere Quellliste im Transform-Modus führt nicht zum Absturz
    Angenommen eine Quell-Entity "sensor.leer" ohne Attribut "forecast"
    Und ein Transform-Helper "Robust" mit Quell-Entity "sensor.leer", Quell-Attribut "forecast" und Attribut-Template "{{ value * 2 }}"
    Dann enthält der Forecast von "Robust" keine Einträge
    Und ist der Helper "Robust" weiterhin funktionsfähig

  Szenario: Ein Rechenfehler im Template lässt den Sensor nicht abstürzen
    Angenommen eine Entity "input_number.divisor" mit Zustand "2"
    Und ein Generate-Helper "Fehleranfaellig" mit Attribut-Template "{{ 10 / (states('input_number.divisor') | float) }}"
    Und der Sensor "Fehleranfaellig" hat den Zustand "5.0"
    Wenn sich der Zustand von "input_number.divisor" auf "0" ändert
    Dann behält der Sensor "Fehleranfaellig" seinen letzten gültigen Zustand "5.0"
    Und ist der Helper "Fehleranfaellig" weiterhin funktionsfähig
