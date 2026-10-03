"""Shared Given/When/Then steps: helper creation, entities, generic assertions.

Creation steps only take the mode-specific mandatory fields (templates,
source entity/attribute). Every other optional field (horizon, update
interval, target attribute, display properties) is set afterwards through
`reconfigure`, i.e. through the same options-flow mechanism REQ 2.5 tests -
there is deliberately no bulk "create with all fields at once" step, to keep
the creation vocabulary small and force reuse of the editing capability.
"""
from __future__ import annotations

from pytest_bdd import given, parsers, then, when

from tests_acceptance.driver import Driver, FlowOutcome

# ---- entities -----------------------------------------------------------


@given(parsers.parse('eine Entity "{entity_id}" mit Zustand "{state}"'))
def an_entity_with_state(driver: Driver, entity_id: str, state: str) -> None:
    driver.set_entity_state(entity_id, state)


@given(parsers.parse('eine Quell-Entity "{entity_id}" mit Zustand "{state}"'))
def a_source_entity_with_state(driver: Driver, entity_id: str, state: str) -> None:
    driver.set_entity_state(entity_id, state)


@given(parsers.parse('eine Quell-Entity "{entity_id}" ohne Attribut "{attribute}"'))
def a_source_entity_without_attribute(driver: Driver, entity_id: str, attribute: str) -> None:
    driver.set_entity_state(entity_id, "unknown")


@given(parsers.parse('eine Quell-Entity "{entity_id}" mit Attribut "{attribute}" und Inhalt:'))
def a_source_entity_with_table_content(
    driver: Driver, entity_id: str, attribute: str, datatable: list[list[str]]
) -> None:
    driver.set_source_forecast(entity_id, attribute, Driver.items_from_table(datatable))


# ---- creation -------------------------------------------------------------


@given(parsers.parse('ein Generate-Helper "{name}" mit Attribut-Template "{template}"'))
def a_generate_helper(driver: Driver, name: str, template: str) -> None:
    outcome = driver.create_generate_helper(name, attribute_template=template)
    assert outcome.success, outcome.errors


@given(
    parsers.parse(
        'ein Transform-Helper "{name}" mit Quell-Entity "{source_entity}", '
        'Quell-Attribut "{source_attribute}" und Attribut-Template "{template}"'
    )
)
def a_transform_helper(
    driver: Driver, name: str, source_entity: str, source_attribute: str, template: str
) -> None:
    outcome = driver.create_transform_helper(
        name,
        source_entity=source_entity,
        source_attribute=source_attribute,
        attribute_template=template,
    )
    assert outcome.success, outcome.errors


@when(
    parsers.parse(
        'versucht wird, einen Generate-Helper "{name}" mit Attribut-Template "{template}" anzulegen'
    ),
    target_fixture="outcome",
)
def attempt_generate_helper(driver: Driver, name: str, template: str) -> FlowOutcome:
    return driver.create_generate_helper(name, attribute_template=template)


@when(
    parsers.parse(
        'versucht wird, einen Generate-Helper "{name}" mit Attribut-Template "{template}" '
        'und State-Template "{state_template}" anzulegen'
    ),
    target_fixture="outcome",
)
def attempt_generate_helper_with_state_template(
    driver: Driver, name: str, template: str, state_template: str
) -> FlowOutcome:
    return driver.create_generate_helper(
        name, attribute_template=template, state_template=state_template
    )


# ---- editing (used across features to set optional/secondary fields) ------


@given(parsers.parse('das State-Template von "{name}" ist "{template}"'))
@when(parsers.parse('das State-Template von "{name}" auf "{template}" geändert wird'))
def set_state_template(driver: Driver, name: str, template: str) -> None:
    outcome = driver.reconfigure(name, state_template=template)
    assert outcome.success, outcome.errors


@given(
    parsers.parse(
        'der Horizont von "{name}" ist {steps:d} Schritte mit je {minutes:d} Minuten'
    )
)
def set_horizon(driver: Driver, name: str, steps: int, minutes: int) -> None:
    outcome = driver.reconfigure(name, horizon_steps=steps, step_minutes=minutes)
    assert outcome.success, outcome.errors


@given(parsers.parse('das Zielattribut von "{name}" heißt "{attribute}"'))
def set_target_attribute(driver: Driver, name: str, attribute: str) -> None:
    outcome = driver.reconfigure(name, target_attribute=attribute)
    assert outcome.success, outcome.errors


@given(parsers.parse('das Update-Intervall von "{name}" ist {minutes:d} Minuten'))
def set_update_interval(driver: Driver, name: str, minutes: int) -> None:
    outcome = driver.reconfigure(name, update_interval_minutes=minutes)
    assert outcome.success, outcome.errors


@given(parsers.parse('die Einheit von "{name}" ist "{unit}"'))
def set_unit(driver: Driver, name: str, unit: str) -> None:
    outcome = driver.reconfigure(name, unit_of_measurement=unit)
    assert outcome.success, outcome.errors


@given(parsers.parse('die Geräteklasse von "{name}" ist "{device_class}"'))
def set_device_class(driver: Driver, name: str, device_class: str) -> None:
    outcome = driver.reconfigure(name, device_class=device_class)
    assert outcome.success, outcome.errors


@given(parsers.parse('die Zustandsklasse von "{name}" ist "{state_class}"'))
def set_state_class(driver: Driver, name: str, state_class: str) -> None:
    outcome = driver.reconfigure(name, state_class=state_class)
    assert outcome.success, outcome.errors


@given(parsers.parse('das Icon von "{name}" ist "{icon}"'))
def set_icon(driver: Driver, name: str, icon: str) -> None:
    outcome = driver.reconfigure(name, icon=icon)
    assert outcome.success, outcome.errors


# ---- generic assertions -----------------------------------------------------


@given(parsers.parse('der Sensor "{name}" hat den Zustand "{expected}"'))
@then(parsers.parse('hat der Sensor "{name}" den Zustand "{expected}"'))
def sensor_has_state(driver: Driver, name: str, expected: str) -> None:
    assert driver.state_of(name) == expected


@then(parsers.parse('behält der Sensor "{name}" seinen letzten gültigen Zustand "{expected}"'))
def sensor_retains_last_valid_state(driver: Driver, name: str, expected: str) -> None:
    assert driver.state_of(name) == expected


@then(parsers.parse('ist der Helper "{name}" weiterhin funktionsfähig'))
def helper_still_alive(driver: Driver, name: str) -> None:
    assert driver.is_still_responsive(name)


@then(parsers.parse('schlägt das Anlegen fehl mit Fehler "{error}" am Feld "{field}"'))
def creation_fails_with_error(outcome: FlowOutcome, error: str, field: str) -> None:
    assert not outcome.success
    assert outcome.errors.get(field) == error


@then(parsers.parse('wird das Anlegen erfolgreich abgeschlossen'))
def creation_succeeds(outcome: FlowOutcome) -> None:
    assert outcome.success, outcome.errors


@then(
    parsers.parse(
        'enthält die gespeicherte Konfiguration von "{name}" keine Info-Bereich-Felder'
    )
)
def stored_config_has_no_info_fields(driver: Driver, name: str) -> None:
    config = driver.raw_stored_config(name)
    assert not any(
        key.startswith("state_template_info_") or key.startswith("attribute_template_info_")
        for key in config
    )
