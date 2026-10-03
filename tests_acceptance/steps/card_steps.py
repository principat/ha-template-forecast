"""Steps for REQ 2.8 - the Forecast Chart dashboard card (see card_driver.py)."""
from __future__ import annotations

import pytest
from pytest_bdd import given, parsers, then, when

from tests_acceptance.card_driver import CardDriver
from tests_acceptance.driver import Driver

# ---- the outside world --------------------------------------------------------


@given(
    parsers.parse(
        'eine Entität "{entity_id}" mit der Einheit "{unit}" und dem Listenattribut "{attribute}" mit Inhalt:'
    )
)
def entity_with_list_attribute_and_unit(
    card: CardDriver, entity_id: str, unit: str, attribute: str, datatable: list[list[str]]
) -> None:
    card.set_entity(entity_id, attribute, Driver.items_from_table(datatable), unit=unit)


@given(
    parsers.parse('eine Entität "{entity_id}" mit dem Listenattribut "{attribute}" mit Inhalt:')
)
def entity_with_list_attribute(
    card: CardDriver, entity_id: str, attribute: str, datatable: list[list[str]]
) -> None:
    card.set_entity(entity_id, attribute, Driver.items_from_table(datatable))


@given(parsers.parse("der aktuelle Zeitpunkt ist {now}"))
def it_is_now(card: CardDriver, now: str) -> None:
    card.now = now


# ---- opening / building the card ------------------------------------------------


@given(
    parsers.parse(
        'eine gespeicherte Karte mit der Entität "{entity}", dem Wertefeld "{key}", '
        'dem Skalierungsfaktor {factor:g} und dem Namen "{name}"'
    )
)
def stored_card_with_details(
    card: CardDriver, entity: str, key: str, factor: float, name: str
) -> None:
    card.load_config(
        {
            "title": "Gespeichert",
            "sources": [
                {
                    "entity": entity,
                    "attribute": "forecast",
                    "time_key": "time",
                    "values": [{"key": key, "factor": factor, "name": name}],
                }
            ],
        }
    )


@given(
    parsers.parse(
        'eine gespeicherte Karte mit der Entität "{entity}" und den Wertefeldern "{first}" '
        'mit Skalierungsfaktor {factor:g} und "{second}" mit Offset {offset:g}'
    )
)
def stored_card_with_two_fields(
    card: CardDriver, entity: str, first: str, factor: float, second: str, offset: float
) -> None:
    card.load_config(
        {
            "sources": [
                {
                    "entity": entity,
                    "attribute": "forecast",
                    "time_key": "time",
                    "values": [
                        {"key": first, "factor": factor},
                        {"key": second, "offset": offset},
                    ],
                }
            ]
        }
    )


@given(parsers.parse('die Karte ist auf den Zeitbereich "{time_range}" eingestellt'))
def time_range(card: CardDriver, time_range: str) -> None:
    card.config["time_range"] = time_range


# ---- editor actions --------------------------------------------------------------


@when(parsers.parse('im Karten-Editor die Entität "{entity}" gewählt wird'))
@given(parsers.parse('im Karten-Editor ist die Entität "{entity}" gewählt'))
def pick_entity(card: CardDriver, entity: str) -> None:
    card.add_source(entity)


@when(parsers.parse('im Karten-Editor die weitere Entität "{entity}" hinzugefügt wird'))
def add_entity(card: CardDriver, entity: str) -> None:
    card.add_source(entity)


@when(parsers.parse('im Karten-Editor die Entität der ersten Quelle auf "{entity}" gewechselt wird'))
def switch_entity(card: CardDriver, entity: str) -> None:
    card.choose_entity(0, entity)


@when(parsers.parse('im Karten-Editor das Listen-Attribut "{attribute}" gewählt wird'))
def pick_attribute(card: CardDriver, attribute: str) -> None:
    card.choose_attribute(0, attribute)


@when(parsers.parse('zusätzlich das Wertefeld "{key}" gewählt wird'))
def pick_additional_field(card: CardDriver, key: str) -> None:
    card.add_value_field(0, key)


@when(parsers.parse('der Skalierungsfaktor des Feldes "{key}" auf {factor:g} gesetzt wird'))
def set_factor(card: CardDriver, key: str, factor: float) -> None:
    card.set_detail(0, key, factor=factor)


@when(parsers.parse('der Offset des Feldes "{key}" auf {offset:g} gesetzt wird'))
def set_offset(card: CardDriver, key: str, offset: float) -> None:
    card.set_detail(0, key, offset=offset)


@when(parsers.parse('der Name des Feldes "{key}" auf "{name}" gesetzt wird'))
def set_name(card: CardDriver, key: str, name: str) -> None:
    card.set_detail(0, key, name=name)


@when(parsers.parse('die Farbe des Feldes "{key}" auf "{color}" gesetzt wird'))
def set_color(card: CardDriver, key: str, color: str) -> None:
    card.set_detail(0, key, color=CardDriver.hex_to_rgb(color))


@when(parsers.parse('die Quelle {position:d} nach oben verschoben wird'))
def move_source_up(card: CardDriver, position: int) -> None:
    card.move_source(position - 1, -1)


@when("der Karten-Editor mit der gespeicherten Konfiguration geöffnet wird")
def open_editor(card: CardDriver) -> None:
    card.open_editor()


# ---- what the editor shows -----------------------------------------------------------


@then(
    parsers.parse(
        'sind im Karten-Editor das Listen-Attribut "{attribute}", das Zeitfeld "{time_key}" '
        'und das Wertefeld "{value_key}" vorbelegt'
    )
)
def preselected(card: CardDriver, attribute: str, time_key: str, value_key: str) -> None:
    form = card.form(0)["form"]
    assert (form["attribute"], form["time_key"], form["value_key"]) == (
        attribute,
        time_key,
        value_key,
    )
    stored = card.stored_source(0)
    assert (stored["attribute"], stored["time_key"]) == (attribute, time_key)


@then(parsers.parse('bietet der Karten-Editor als weitere Wertefelder "{keys}" an'))
def offers_additional_fields(card: CardDriver, keys: str) -> None:
    offered = card.form(0)["info"]["numericKeys"]
    expected = [k.strip() for k in keys.split(",")]
    assert [k for k in offered if k != card.form(0)["form"]["value_key"]] == expected


@then(
    parsers.parse(
        'zeigt der Karten-Editor für das Feld "{key}" den Skalierungsfaktor {factor:g} '
        'und den Namen "{name}"'
    )
)
def editor_shows_details(card: CardDriver, key: str, factor: float, name: str) -> None:
    assert card.shown is not None
    form = card.shown["form"]
    slot = [form["value_key"], *form["extra_keys"]].index(key)
    detail = form[f"detail_{slot}"]
    assert detail["factor"] == factor
    assert detail["name"] == name


@then("ist die gespeicherte Konfiguration der Karte unverändert")
def config_unchanged(card: CardDriver) -> None:
    assert card.stored_source(0) == card.opened_with


@then(
    parsers.parse(
        'bleibt für das Feld "{key}" der Skalierungsfaktor {factor:g} gespeichert'
    )
)
def factor_kept(card: CardDriver, key: str, factor: float) -> None:
    values = {v["key"]: v for v in card.stored_source(0)["values"]}
    assert values[key].get("factor") == factor


@then(parsers.parse('bleibt für das Feld "{key}" der Offset {offset:g} gespeichert'))
def offset_kept(card: CardDriver, key: str, offset: float) -> None:
    values = {v["key"]: v for v in card.stored_source(0)["values"]}
    assert values[key].get("offset") == offset


@then(parsers.parse('enthält die Konfiguration der Quelle nur das Wertefeld "{key}"'))
def only_value_field(card: CardDriver, key: str) -> None:
    assert [v["key"] for v in card.stored_source(0)["values"]] == [key]


# ---- what the chart shows ---------------------------------------------------------------


@then(parsers.parse("zeigt das Diagramm {count:d} Linien"))
@then(parsers.parse("zeigt das Diagramm {count:d} Linie"))
def line_count(card: CardDriver, count: int) -> None:
    assert len(card.series()["series"]) == count


@then(parsers.parse('zeigt die Linie "{name}" an Position {position:d} den Wert {value:g}'))
def line_value(card: CardDriver, name: str, position: int, value: float) -> None:
    assert card.line(name)["y"][position - 1] == pytest.approx(value)


@then(parsers.parse('hat die Linie "{name}" {count:d} Punkte'))
def line_points(card: CardDriver, name: str, count: int) -> None:
    assert len(card.line(name)["y"]) == count


@then(parsers.parse('hat die Linie "{name}" die Farbe "{color}"'))
def line_color(card: CardDriver, name: str, color: str) -> None:
    assert card.line(name)["color"].lower() == color.lower()


@then(parsers.parse('liegt die Linie "{name}" auf der {side} Y-Achse'))
def line_axis(card: CardDriver, name: str, side: str) -> None:
    assert card.line(name)["axis"] == {"linken": "left", "rechten": "right"}[side]


@then(parsers.parse('lautet die Reihenfolge der Linien "{names}"'))
def line_order(card: CardDriver, names: str) -> None:
    assert [s["name"] for s in card.series()["series"]] == [n.strip() for n in names.split(",")]


@then(parsers.parse('meldet das Diagramm für "{entity}" den Hinweis "{code}"'))
def chart_reports_error(card: CardDriver, entity: str, code: str) -> None:
    errors = card.series()["errors"]
    assert {"entity": entity, "code": code} in [
        {"entity": e["entity"], "code": e["code"]} for e in errors
    ]
