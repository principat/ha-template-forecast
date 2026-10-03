# language: de
# REQ 2.2 — docs/REQUIREMENTS.md Abschnitt 2.2
@REQ-2.2
Funktionalität: Attribut- und State-Templates

  Als Nutzer möchte ich mit Jinja2-Templates die einzelnen Vorhersage-Einträge
  sowie den Sensor-Zustand berechnen, mit klar definierten Variablen je Modus,
  und verständliche Fehler bekommen, wenn ein Template ungültig ist oder beim
  Rendern fehlschlägt - bevor der Helper überhaupt angelegt wird.

  Szenario: Ein syntaktisch ungültiges Template verhindert das Anlegen
    Wenn versucht wird, einen Generate-Helper "Kaputt" mit Attribut-Template "{{ das ist kein gueltiges jinja {{" anzulegen
    Dann schlägt das Anlegen fehl mit Fehler "invalid_template" am Feld "attribute_template"

  Szenario: Ein im falschen Modus verwendetes Template scheitert beim Test-Rendern
    Wenn versucht wird, einen Generate-Helper "FalscheVariable" mit Attribut-Template "{{ item.start_time | length }}" anzulegen
    Dann schlägt das Anlegen fehl mit Fehler "attribute_template_render_error" am Feld "attribute_template"

  Szenario: Im Generate-Modus stehen index und horizon im Attribut-Template zur Verfügung
    Angenommen ein Generate-Helper "Anteil" mit Attribut-Template "{{ index / horizon }}"
    Und der Horizont von "Anteil" ist 4 Schritte mit je 60 Minuten
    Dann hat der Eintrag mit Index 2 im Forecast von "Anteil" den Wert "0.5"

  Szenario: Ein Attribut-Template kann als Dict zusätzliche Felder in den Eintrag mischen
    Angenommen ein Generate-Helper "Erweitert" mit Attribut-Template "{{ {'value': index, 'kategorie': 'test'} }}"
    Dann hat der Eintrag mit Index 0 im Forecast von "Erweitert" den Wert "0"
    Und hat der Eintrag mit Index 0 im Forecast von "Erweitert" das Feld "kategorie" mit Wert "test"

  Szenario: Das State-Template hat im Transform-Modus Zugriff auf die Quelle
    Angenommen eine Quell-Entity "sensor.rohdaten" mit Zustand "42"
    Und eine Quell-Entity "sensor.rohdaten" mit Attribut "forecast" und Inhalt:
      | value |
      | 1     |
    Und ein Transform-Helper "MitQuelle" mit Quell-Entity "sensor.rohdaten", Quell-Attribut "forecast" und Attribut-Template "{{ value }}"
    Und das State-Template von "MitQuelle" ist "{{ source }}"
    Dann hat der Sensor "MitQuelle" den Zustand "42"

  Szenario: Das State-Template ist im Generate-Modus mit dem ersten Forecast-Wert vorbelegt
    Wenn das Anlegeformular eines Generate-Helpers geöffnet wird
    Dann ist das State-Template mit "{{ forecast[0].value }}" vorbelegt

  Szenario: Das State-Template ist im Transform-Modus mit dem ersten Forecast-Wert vorbelegt
    Wenn das Anlegeformular eines Transform-Helpers geöffnet wird
    Dann ist das State-Template mit "{{ forecast[0].value }}" vorbelegt

  Szenario: Das State-Template steht im Anlegeformular unterhalb des Attribut-Templates
    Wenn das Anlegeformular eines Generate-Helpers geöffnet wird
    Dann steht das Feld "state_template" im Anlegeformular unterhalb des Feldes "attribute_template"

  Szenario: Ohne eigenes State-Template zeigt der Sensor den ersten Forecast-Wert
    Angenommen ein Generate-Helper "Vorbelegt" mit Attribut-Template "{{ index + 5 }}"
    Dann hat der Sensor "Vorbelegt" den Zustand "5"
