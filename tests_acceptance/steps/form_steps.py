"""Steps about the creation form itself (REQ 2.2: pre-filled State-Template, field order)."""
from __future__ import annotations

from typing import Any

from pytest_bdd import parsers, then, when

from custom_components.template_forecast.const import MODE_GENERATE, MODE_TRANSFORM
from tests_acceptance.driver import Driver

_MODES = {"Generate": MODE_GENERATE, "Transform": MODE_TRANSFORM}


@when(
    parsers.parse("das Anlegeformular eines {mode}-Helpers geöffnet wird"),
    target_fixture="form",
)
def open_creation_form(driver: Driver, mode: str) -> dict[str, Any]:
    return driver.creation_form(_MODES[mode])


@then(parsers.parse('ist das State-Template mit "{template}" vorbelegt'))
def state_template_prefilled(form: dict[str, Any], template: str) -> None:
    assert form["defaults"]["state_template"] == template


@then(
    parsers.parse(
        'steht das Feld "{lower}" im Anlegeformular unterhalb des Feldes "{upper}"'
    )
)
def field_below(form: dict[str, Any], lower: str, upper: str) -> None:
    assert form["fields"].index(lower) > form["fields"].index(upper)
