"""Tests für Config- und Options-Flow der Template Forecast Integration."""
from __future__ import annotations

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.template_forecast.const import (
    CONF_ATTRIBUTE_TEMPLATE,
    CONF_HORIZON_STEPS,
    CONF_MODE,
    CONF_NAME,
    CONF_SOURCE_ATTRIBUTE,
    CONF_SOURCE_ENTITY,
    CONF_STATE_TEMPLATE,
    CONF_STEP_MINUTES,
    CONF_TARGET_ATTRIBUTE,
    DOMAIN,
    MODE_GENERATE,
    MODE_TRANSFORM,
)


async def test_generate_flow_creates_entry(hass: HomeAssistant) -> None:
    """Kompletter Generate-Flow legt eine Config-Entry mit korrekten Daten an."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_NAME: "Preis Forecast", CONF_MODE: MODE_GENERATE},
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "generate"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_HORIZON_STEPS: 4,
            CONF_STEP_MINUTES: 60,
            CONF_STATE_TEMPLATE: "{{ forecast[0].value }}",
            CONF_ATTRIBUTE_TEMPLATE: "{{ index * 2 }}",
            CONF_TARGET_ATTRIBUTE: "forecast",
        },
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "Preis Forecast"
    data = result["data"]
    assert data[CONF_MODE] == MODE_GENERATE
    assert data[CONF_HORIZON_STEPS] == 4
    assert data[CONF_ATTRIBUTE_TEMPLATE] == "{{ index * 2 }}"


async def test_transform_flow_creates_entry(hass: HomeAssistant) -> None:
    """Kompletter Transform-Flow fragt zusätzlich die Quell-Entität ab."""
    hass.states.async_set("sensor.source", "on", {"forecast": []})

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_NAME: "Transformierter Forecast", CONF_MODE: MODE_TRANSFORM},
    )
    assert result["step_id"] == "transform_source"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_SOURCE_ENTITY: "sensor.source"}
    )
    assert result["step_id"] == "transform"
    assert "sensor.source" in result["description_placeholders"]["source_entity"]

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_SOURCE_ATTRIBUTE: "forecast",
            CONF_STATE_TEMPLATE: "{{ source }}",
            CONF_ATTRIBUTE_TEMPLATE: "{{ value * 2 }}",
        },
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    data = result["data"]
    assert data[CONF_MODE] == MODE_TRANSFORM
    assert data[CONF_SOURCE_ENTITY] == "sensor.source"
    assert data[CONF_SOURCE_ATTRIBUTE] == "forecast"


async def test_generate_flow_rejects_invalid_template(hass: HomeAssistant) -> None:
    """Ein syntaktisch ungültiges Template führt zu einem Formularfehler statt Absturz."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_NAME: "Kaputt", CONF_MODE: MODE_GENERATE},
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_HORIZON_STEPS: 4,
            CONF_STEP_MINUTES: 60,
            CONF_STATE_TEMPLATE: "{{ this is not valid jinja {{",
            CONF_ATTRIBUTE_TEMPLATE: "{{ index }}",
            CONF_TARGET_ATTRIBUTE: "forecast",
        },
    )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"][CONF_STATE_TEMPLATE] == "invalid_template"


async def test_options_flow_updates_existing_entry(hass: HomeAssistant) -> None:
    """Ein bestehender Helfer lässt sich über den Options-Flow bearbeiten."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_NAME: "Bearbeitbar", CONF_MODE: MODE_GENERATE},
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_HORIZON_STEPS: 4,
            CONF_STEP_MINUTES: 60,
            CONF_STATE_TEMPLATE: "{{ forecast[0].value }}",
            CONF_ATTRIBUTE_TEMPLATE: "{{ index }}",
            CONF_TARGET_ATTRIBUTE: "forecast",
        },
    )
    entry = hass.config_entries.async_entries(DOMAIN)[0]

    options_result = await hass.config_entries.options.async_init(entry.entry_id)
    assert options_result["type"] == FlowResultType.FORM
    assert options_result["step_id"] == "init"

    options_result = await hass.config_entries.options.async_configure(
        options_result["flow_id"],
        {
            CONF_HORIZON_STEPS: 8,
            CONF_STEP_MINUTES: 30,
            CONF_STATE_TEMPLATE: "{{ forecast[0].value }}",
            CONF_ATTRIBUTE_TEMPLATE: "{{ index * 10 }}",
            CONF_TARGET_ATTRIBUTE: "forecast",
        },
    )

    assert options_result["type"] == FlowResultType.CREATE_ENTRY
    assert entry.options[CONF_HORIZON_STEPS] == 8
    assert entry.options[CONF_ATTRIBUTE_TEMPLATE] == "{{ index * 10 }}"
