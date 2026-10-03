# language: de
# REQ 2.6 (nur der Persistenz-Aspekt) — docs/REQUIREMENTS.md Abschnitt 2.6
#
# Das eigentliche UI-Rendering der Info-Bereiche (Einklappen, Syntax-
# Highlighting im Beispiel-Feld, Markdown-Darstellung der Beschreibung,
# en/de-Synchronität) wird hier bewusst NICHT getestet - das übernehmen
# tests_e2e/ (echter Browser) und tests/test_translations.py (ICU/Markdown/
# en-de-Abgleich). Diese Datei prüft ausschließlich die eine Garantie, die
# sich black-box beobachten lässt: dass die reinen Anzeige-Platzhalter nie
# in den gespeicherten Konfigurationsdaten landen, auch nicht bei direktem
# API-Zugriff, der die Frontend-Absicherung umgeht.
@REQ-2.6
Funktionalität: Info-Bereiche sind rein informativ und werden nie gespeichert

  Szenario: Die Info-Bereich-Platzhalter landen nie in der gespeicherten Konfiguration
    Angenommen ein Generate-Helper "MitInfo" mit Attribut-Template "{{ index }}"
    Dann enthält die gespeicherte Konfiguration von "MitInfo" keine Info-Bereich-Felder

  Szenario: Die Info-Bereich-Platzhalter landen auch nach dem Bearbeiten nicht in der Konfiguration
    Angenommen ein Generate-Helper "MitInfoBearbeitet" mit Attribut-Template "{{ index }}"
    Wenn das Attribut-Template von "MitInfoBearbeitet" auf "{{ index * 2 }}" geändert wird
    Dann enthält die gespeicherte Konfiguration von "MitInfoBearbeitet" keine Info-Bereich-Felder
