# language: de
# REQ 2.3 — docs/REQUIREMENTS.md Abschnitt 2.3
@REQ-2.3
Funktionalität: Weitere Konfigurationsfelder

  Als Nutzer möchte ich den Namen des Zielattributs, das Update-Intervall und
  optionale Anzeige-Eigenschaften (Einheit, Geräteklasse, Zustandsklasse,
  Icon) konfigurieren können, ohne dass diese die eigentliche Berechnung
  beeinflussen.

  Szenario: Der Name des Zielattributs ist konfigurierbar
    Angenommen ein Generate-Helper "Umbenannt" mit Attribut-Template "{{ index }}"
    Und das Zielattribut von "Umbenannt" heißt "predictions"
    Dann hat der Eintrag mit Index 0 im Attribut "predictions" von "Umbenannt" den Wert "0"

  Szenario: Die periodische Neuberechnung läuft auch ohne abhängige Entities weiter
    Angenommen ein Generate-Helper "Takt" mit Attribut-Template "{{ 7 }}"
    Und das Update-Intervall von "Takt" ist 5 Minuten
    Wenn 5 Minuten Zeit vergehen
    Dann hat der Eintrag mit Index 0 im Forecast von "Takt" den Wert "7"
    Und ist der Helper "Takt" weiterhin funktionsfähig

  Szenario: Anzeige-Eigenschaften wirken sich nicht auf die berechneten Werte aus
    Angenommen ein Generate-Helper "Angezeigt" mit Attribut-Template "{{ index }}"
    Und die Einheit von "Angezeigt" ist "€/kWh"
    Und die Geräteklasse von "Angezeigt" ist "monetary"
    Und die Zustandsklasse von "Angezeigt" ist "measurement"
    Und das Icon von "Angezeigt" ist "mdi:currency-eur"
    Dann hat der Eintrag mit Index 0 im Forecast von "Angezeigt" den Wert "0"
