"""Steps specific to REQ 2.4 - automatic recomputation."""
from __future__ import annotations

from pytest_bdd import parsers, then, when

from tests_acceptance.driver import Driver


@when(parsers.parse('sich der Zustand von "{entity_id}" auf "{state}" ändert'))
def change_entity_state(driver: Driver, entity_id: str, state: str) -> None:
    driver.set_entity_state(entity_id, state)


@when(parsers.parse('das Attribut "{attribute}" von "{entity_id}" geändert wird auf:'))
def change_source_attribute(
    driver: Driver, entity_id: str, attribute: str, datatable: list[list[str]]
) -> None:
    driver.set_source_forecast(entity_id, attribute, Driver.items_from_table(datatable))


@when(parsers.parse('{minutes:d} Minuten Zeit vergehen'))
def time_passes(driver: Driver, minutes: int) -> None:
    driver.advance_time(minutes)


@when(parsers.parse('Home Assistant neu gestartet wird, während "{name}" existiert'))
def restart_ha(driver: Driver, name: str) -> None:
    driver.restart(name)


@then(
    parsers.parse(
        'hat der Eintrag mit Index {index:d} im Forecast von "{name}" den Wert "{value}"'
    )
)
def forecast_entry_has_value(driver: Driver, index: int, name: str, value: str) -> None:
    forecast = driver.forecast_of(name)
    assert str(forecast[index]["value"]) == value


@then(parsers.parse('enthält der Forecast von "{name}" genau einen Eintrag mit Wert "{value}"'))
def forecast_has_one_entry_with_value(driver: Driver, name: str, value: str) -> None:
    forecast = driver.forecast_of(name)
    assert len(forecast) == 1
    assert str(forecast[0]["value"]) == value


@then(parsers.parse('enthält der Forecast von "{name}" keine Einträge'))
def forecast_is_empty(driver: Driver, name: str) -> None:
    assert driver.forecast_of(name) == []


@then(
    parsers.parse(
        'hat der Eintrag mit Index {index:d} im Attribut "{attribute}" von "{name}" den Wert "{value}"'
    )
)
def forecast_entry_in_named_attribute_has_value(
    driver: Driver, index: int, attribute: str, name: str, value: str
) -> None:
    forecast = driver.forecast_of(name, target_attribute=attribute)
    assert str(forecast[index]["value"]) == value


@then(
    parsers.parse(
        'hat der Eintrag mit Index {index:d} im Forecast von "{name}" das Feld "{field}" mit Wert "{value}"'
    )
)
def forecast_entry_has_field_value(
    driver: Driver, index: int, name: str, field: str, value: str
) -> None:
    forecast = driver.forecast_of(name)
    assert str(forecast[index][field]) == value
