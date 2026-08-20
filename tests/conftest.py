"""Gemeinsame Fixtures für die Template-Forecast-Tests."""
from __future__ import annotations

import pytest

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """custom_components/ automatisch für jeden Test verfügbar machen."""
    yield
