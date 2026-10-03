# language: de
# REQ 2.5 — docs/REQUIREMENTS.md Abschnitt 2.5
@REQ-2.5
Funktionalität: Bearbeitbarkeit nach dem Anlegen

  Als Nutzer möchte ich einen bereits angelegten Helper jederzeit über die
  Bearbeiten-Funktion anpassen können - alle Felder außer dem Modus - und
  darauf vertrauen, dass eine Änderung sofort wirkt, ohne Home Assistant neu
  starten zu müssen.

  Szenario: Eine Änderung am Attribut-Template wirkt sofort, ohne Neustart
    Angenommen ein Generate-Helper "Editierbar" mit Attribut-Template "{{ index }}"
    Wenn das Attribut-Template von "Editierbar" auf "{{ index * 100 }}" geändert wird
    Dann hat der Eintrag mit Index 1 im Forecast von "Editierbar" den Wert "100"

  Szenario: Die Quell-Entity ist im Transform-Modus nachträglich änderbar
    Angenommen eine Quell-Entity "sensor.quelle_a" mit Attribut "forecast" und Inhalt:
      | value |
      | 1     |
    Und eine Quell-Entity "sensor.quelle_b" mit Attribut "forecast" und Inhalt:
      | value |
      | 9     |
    Und ein Transform-Helper "Umgehaengt" mit Quell-Entity "sensor.quelle_a", Quell-Attribut "forecast" und Attribut-Template "{{ value }}"
    Wenn die Quell-Entity von "Umgehaengt" auf "sensor.quelle_b" geändert wird
    Dann enthält der Forecast von "Umgehaengt" genau einen Eintrag mit Wert "9"

  Szenario: Zielattribut, Update-Intervall und Anzeige-Eigenschaften bleiben änderbar
    Angenommen ein Generate-Helper "AllesOffen" mit Attribut-Template "{{ index }}"
    Dann bietet die Bearbeitung von "AllesOffen" ein Feld "target_attribute" an
    Und bietet die Bearbeitung von "AllesOffen" ein Feld "update_interval_minutes" an
    Und bietet die Bearbeitung von "AllesOffen" ein Feld "unit_of_measurement" an
    Und bietet die Bearbeitung von "AllesOffen" ein Feld "device_class" an
    Und bietet die Bearbeitung von "AllesOffen" ein Feld "state_class" an
    Und bietet die Bearbeitung von "AllesOffen" ein Feld "icon" an
