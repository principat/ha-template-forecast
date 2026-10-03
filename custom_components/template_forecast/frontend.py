"""Serves the Forecast Chart dashboard card.

This module is the *only* link between the integration and the card. The card itself lives in
``/frontend`` (sources) and ``www/forecast-chart-card.js`` (build output) and has no
dependency on the rest of the integration. To move the card into its own repository, move
those two and delete this module together with its call in ``__init__.py``.
"""
from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

CARD_FILE = "forecast-chart-card.js"
# Deliberately independent of the integration domain, so dashboards keep working if the card
# is published separately later.
CARD_URL = f"/forecast-chart-card/{CARD_FILE}"
_BUNDLE = Path(__file__).parent / "www" / CARD_FILE
_REGISTERED_KEY = "forecast_chart_card_registered"


async def async_register_card(hass: HomeAssistant, version: str) -> None:
    """Expose the card bundle and load it in the frontend. Never raises."""
    if hass.data.get(_REGISTERED_KEY):
        return
    if not _BUNDLE.is_file():
        _LOGGER.debug("Forecast chart card bundle not found at %s", _BUNDLE)
        return
    if getattr(hass, "http", None) is None or "frontend" not in hass.config.components:
        _LOGGER.debug("HTTP/frontend not available, skipping forecast chart card")
        return
    try:
        from homeassistant.components.frontend import add_extra_js_url
        from homeassistant.components.http import StaticPathConfig

        await hass.http.async_register_static_paths(
            [StaticPathConfig(CARD_URL, str(_BUNDLE), cache_headers=False)]
        )
        # the version in the query string makes browsers fetch the new file after an update
        add_extra_js_url(hass, f"{CARD_URL}?v={version}")
    except Exception:  # noqa: BLE001 - the card is optional, never break the integration
        _LOGGER.exception("Could not register the forecast chart card")
        return
    hass.data[_REGISTERED_KEY] = True
