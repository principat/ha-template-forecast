"""Shared fixtures for the acceptance suite.

Deliberately does not import tests/conftest.py: this suite is a
self-contained sibling of tests/ and tests_e2e/ (same principle
tests_e2e/ already follows with its own pytest.ini) and should stay
independently evolvable.
"""
from __future__ import annotations

import pytest

from tests_acceptance.card_driver import CardDriver
from tests_acceptance.driver import Driver

pytest_plugins = (
    "pytest_homeassistant_custom_component",
    "tests_acceptance.steps.common_steps",
    "tests_acceptance.steps.recompute_steps",
    "tests_acceptance.steps.editing_steps",
    "tests_acceptance.steps.form_steps",
    "tests_acceptance.steps.card_steps",
)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


@pytest.fixture
def driver(hass) -> Driver:
    return Driver(hass)


@pytest.fixture
def card() -> CardDriver:
    return CardDriver()
