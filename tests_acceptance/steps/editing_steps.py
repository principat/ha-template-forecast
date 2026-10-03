"""Steps specific to REQ 2.5 - editing an already-created helper, and the
REQ 2.1 "mode is fixed after creation" guarantee (checked via the same
options-flow schema introspection)."""
from __future__ import annotations

from pytest_bdd import parsers, then, when

from tests_acceptance.driver import Driver


@when(parsers.parse('das Attribut-Template von "{name}" auf "{template}" geändert wird'))
def change_attribute_template(driver: Driver, name: str, template: str) -> None:
    outcome = driver.reconfigure(name, attribute_template=template)
    assert outcome.success, outcome.errors


@when(parsers.parse('die Quell-Entity von "{name}" auf "{source_entity}" geändert wird'))
def change_source_entity(driver: Driver, name: str, source_entity: str) -> None:
    outcome = driver.reconfigure(name, source_entity=source_entity)
    assert outcome.success, outcome.errors


@then(parsers.parse('bietet die Bearbeitung von "{name}" kein Feld zur Änderung des Modus an'))
def mode_field_not_editable(driver: Driver, name: str) -> None:
    assert "mode" not in driver.options_flow_schema_keys(name)


@then(parsers.parse('bietet die Bearbeitung von "{name}" ein Feld "{field}" an'))
def field_is_editable(driver: Driver, name: str, field: str) -> None:
    assert field in driver.options_flow_schema_keys(name)
