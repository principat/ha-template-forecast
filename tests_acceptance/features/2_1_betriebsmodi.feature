# language: de
# REQ 2.1 — docs/REQUIREMENTS.md Abschnitt 2.1
@REQ-2.1
Funktionalität: Zwei Betriebsmodi (Generate und Transform)

  Als Nutzer möchte ich beim Anlegen eines Helpers zwischen zwei Modi wählen -
  Generate (fester Planungshorizont) oder Transform (Umwandlung einer
  bestehenden Vorhersageliste) - und mich darauf verlassen können, dass der
  Modus danach nicht mehr versehentlich verändert werden kann.

  Szenario: Ein Generate-Helper erzeugt eine Vorhersage über einen festen Horizont
    Angenommen ein Generate-Helper "Rampe" mit Attribut-Template "{{ index }}"
    Und der Horizont von "Rampe" ist 3 Schritte mit je 60 Minuten
    Dann hat der Eintrag mit Index 0 im Forecast von "Rampe" den Wert "0"
    Und hat der Eintrag mit Index 2 im Forecast von "Rampe" den Wert "2"

  Szenario: Ein Transform-Helper transformiert die Liste einer Quell-Entity
    Angenommen eine Quell-Entity "sensor.rohdaten" mit Attribut "forecast" und Inhalt:
      | value |
      | 3     |
      | 4     |
    Und ein Transform-Helper "Verdoppelt" mit Quell-Entity "sensor.rohdaten", Quell-Attribut "forecast" und Attribut-Template "{{ value * 2 }}"
    Dann hat der Eintrag mit Index 0 im Forecast von "Verdoppelt" den Wert "6"
    Und hat der Eintrag mit Index 1 im Forecast von "Verdoppelt" den Wert "8"

  Szenario: Der Modus ist nach dem Anlegen nicht mehr änderbar
    Angenommen ein Generate-Helper "Fest" mit Attribut-Template "{{ index }}"
    Dann bietet die Bearbeitung von "Fest" kein Feld zur Änderung des Modus an
    Und bietet die Bearbeitung von "Fest" ein Feld "attribute_template" an
