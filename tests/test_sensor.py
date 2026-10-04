"""Tests for the sensor's forecast calculation (Generate & Transform)."""
from __future__ import annotations

from homeassistant.core import HomeAssistant
from custom_components.template_forecast.const import (
    CONF_ATTRIBUTE_TEMPLATE,
    CONF_DEVICE_CLASS,
    CONF_HORIZON_STEPS,
    CONF_ICON,
    CONF_MODE,
    CONF_NAME,
    CONF_SOURCE_ATTRIBUTE,
    CONF_SOURCE_ENTITY,
    CONF_STATE_CLASS,
    CONF_STATE_TEMPLATE,
    CONF_STEP_MINUTES,
    CONF_TARGET_ATTRIBUTE,
    DOMAIN,
    MODE_GENERATE,
    MODE_TRANSFORM,
)
from homeassistant.const import CONF_UNIT_OF_MEASUREMENT
from pytest_homeassistant_custom_component.common import MockConfigEntry


async def test_generate_mode_builds_linear_forecast(hass: HomeAssistant) -> None:
    """The start/end use case: linear ramp over the horizon."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Price Forecast",
        data={
            CONF_MODE: MODE_GENERATE,
            CONF_NAME: "Price Forecast",
            CONF_HORIZON_STEPS: 5,
            CONF_STEP_MINUTES: 60,
            CONF_STATE_TEMPLATE: "{{ forecast[0].value }}",
            CONF_ATTRIBUTE_TEMPLATE: (
                "{{ (10 + (20 - 10) * index / 4) | round(2) }}"
            ),
            CONF_TARGET_ATTRIBUTE: "forecast",
        },
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.price_forecast")
    assert state is not None
    assert state.state == "10.0"

    forecast = state.attributes["forecast"]
    assert len(forecast) == 5
    assert forecast[0]["value"] == 10.0
    assert forecast[-1]["value"] == 20.0
    # even spacing: step 2 is in the middle
    assert forecast[2]["value"] == 15.0
    # timestamps must be strictly ascending
    timestamps = [f["time"] for f in forecast]
    assert timestamps == sorted(timestamps)


async def test_generate_mode_merges_dict_template_result(hass: HomeAssistant) -> None:
    """If the template returns a dict, its keys are merged into the forecast item."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Multi Generate",
        data={
            CONF_MODE: MODE_GENERATE,
            CONF_NAME: "Multi Generate",
            CONF_HORIZON_STEPS: 2,
            CONF_STEP_MINUTES: 60,
            CONF_STATE_TEMPLATE: "{{ forecast[0].value }}",
            CONF_ATTRIBUTE_TEMPLATE: (
                "{{ {'value': index * 10, 'condition': 'sunny'} }}"
            ),
            CONF_TARGET_ATTRIBUTE: "forecast",
        },
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.multi_generate")
    assert state is not None

    forecast = state.attributes["forecast"]
    assert [f["value"] for f in forecast] == [0, 10]
    assert [f["condition"] for f in forecast] == ["sunny", "sunny"]
    # time keys are still present alongside the merged keys
    assert "time" in forecast[0]


async def test_transform_mode_applies_template_per_item(hass: HomeAssistant) -> None:
    """An existing forecast list is transformed item by item."""
    hass.states.async_set(
        "sensor.source_forecast",
        "unknown",
        {
            "forecast": [
                {"datetime": "2026-08-20T10:00:00+00:00", "value": 10},
                {"datetime": "2026-08-20T11:00:00+00:00", "value": 20},
                {"datetime": "2026-08-20T12:00:00+00:00", "value": 30},
            ]
        },
    )

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Doubled",
        data={
            CONF_MODE: MODE_TRANSFORM,
            CONF_NAME: "Doubled",
            CONF_SOURCE_ENTITY: "sensor.source_forecast",
            CONF_SOURCE_ATTRIBUTE: "forecast",
            CONF_STATE_TEMPLATE: "{{ forecast | length }}",
            CONF_ATTRIBUTE_TEMPLATE: "{{ value * 2 }}",
            CONF_TARGET_ATTRIBUTE: "forecast_doubled",
        },
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.doubled")
    assert state is not None
    assert state.state == "3"

    forecast = state.attributes["forecast_doubled"]
    assert [f["value"] for f in forecast] == [20, 40, 60]
    # the time of the source entry is carried over as "time" - and nothing else is
    assert forecast[0] == {"time": "2026-08-20T10:00:00+00:00", "value": 20}
    assert all(set(f) == {"time", "value"} for f in forecast)


async def test_transform_mode_merges_dict_template_result(
    hass: HomeAssistant,
) -> None:
    """If the template returns a dict, its keys are merged into the item."""
    hass.states.async_set(
        "sensor.source_forecast",
        "unknown",
        {
            "forecast": [
                {"datetime": "2026-08-20T10:00:00+00:00", "value": 10},
                {"datetime": "2026-08-20T11:00:00+00:00", "value": 20},
            ]
        },
    )

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Multi",
        data={
            CONF_MODE: MODE_TRANSFORM,
            CONF_NAME: "Multi",
            CONF_SOURCE_ENTITY: "sensor.source_forecast",
            CONF_SOURCE_ATTRIBUTE: "forecast",
            CONF_STATE_TEMPLATE: "{{ forecast | length }}",
            CONF_ATTRIBUTE_TEMPLATE: (
                "{{ {'value': value * 2, 'condition': 'sunny'} }}"
            ),
            CONF_TARGET_ATTRIBUTE: "forecast_multi",
        },
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.multi")
    assert state is not None

    forecast = state.attributes["forecast_multi"]
    assert [f["value"] for f in forecast] == [20, 40]
    assert [f["condition"] for f in forecast] == ["sunny", "sunny"]
    # the time is carried over, the original "datetime" key is not
    assert forecast[0]["time"] == "2026-08-20T10:00:00+00:00"
    assert "datetime" not in forecast[0]


async def test_transform_mode_recomputes_on_source_update(hass: HomeAssistant) -> None:
    """When the source entity changes, the forecast helper updates automatically."""
    hass.states.async_set(
        "sensor.source_forecast",
        "unknown",
        {"forecast": [{"datetime": "2026-08-20T10:00:00+00:00", "value": 1}]},
    )

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Live",
        data={
            CONF_MODE: MODE_TRANSFORM,
            CONF_NAME: "Live",
            CONF_SOURCE_ENTITY: "sensor.source_forecast",
            CONF_SOURCE_ATTRIBUTE: "forecast",
            CONF_STATE_TEMPLATE: "{{ forecast[0].value }}",
            CONF_ATTRIBUTE_TEMPLATE: "{{ value }}",
            CONF_TARGET_ATTRIBUTE: "forecast",
        },
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert hass.states.get("sensor.live").state == "1"

    hass.states.async_set(
        "sensor.source_forecast",
        "unknown",
        {"forecast": [{"datetime": "2026-08-20T10:00:00+00:00", "value": 99}]},
    )
    await hass.async_block_till_done()

    assert hass.states.get("sensor.live").state == "99"


async def test_transform_mode_handles_missing_source_attribute(
    hass: HomeAssistant,
) -> None:
    """If the configured source attribute is missing, an empty but valid list results."""
    hass.states.async_set("sensor.source_forecast", "unknown", {})

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Empty",
        data={
            CONF_MODE: MODE_TRANSFORM,
            CONF_NAME: "Empty",
            CONF_SOURCE_ENTITY: "sensor.source_forecast",
            CONF_SOURCE_ATTRIBUTE: "forecast",
            CONF_STATE_TEMPLATE: "{{ forecast | length }}",
            CONF_ATTRIBUTE_TEMPLATE: "{{ value }}",
            CONF_TARGET_ATTRIBUTE: "forecast",
        },
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.empty")
    assert state.state == "0"
    assert state.attributes["forecast"] == []


async def test_standard_sensor_properties_are_applied(hass: HomeAssistant) -> None:
    """unit_of_measurement, device_class, state_class and icon end up on the entity."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Price with Properties",
        data={
            CONF_MODE: MODE_GENERATE,
            CONF_NAME: "Price with Properties",
            CONF_HORIZON_STEPS: 2,
            CONF_STEP_MINUTES: 60,
            CONF_STATE_TEMPLATE: "{{ forecast[0].value }}",
            CONF_ATTRIBUTE_TEMPLATE: "{{ index }}",
            CONF_TARGET_ATTRIBUTE: "forecast",
            CONF_UNIT_OF_MEASUREMENT: "EUR/kWh",
            CONF_DEVICE_CLASS: "monetary",
            CONF_STATE_CLASS: "measurement",
            CONF_ICON: "mdi:currency-eur",
        },
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.price_with_properties")
    assert state is not None
    assert state.attributes["unit_of_measurement"] == "EUR/kWh"
    assert state.attributes["device_class"] == "monetary"
    assert state.attributes["state_class"] == "measurement"
    assert state.attributes["icon"] == "mdi:currency-eur"


async def test_standard_sensor_properties_default_to_none(hass: HomeAssistant) -> None:
    """Without values, device_class/state_class/icon stay untouched (no crash)."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Without Extras",
        data={
            CONF_MODE: MODE_GENERATE,
            CONF_NAME: "Without Extras",
            CONF_HORIZON_STEPS: 2,
            CONF_STEP_MINUTES: 60,
            CONF_STATE_TEMPLATE: "{{ forecast[0].value }}",
            CONF_ATTRIBUTE_TEMPLATE: "{{ index }}",
            CONF_TARGET_ATTRIBUTE: "forecast",
        },
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.without_extras")
    assert state is not None
    assert state.attributes.get("device_class") is None
    assert state.attributes.get("state_class") is None


async def test_transform_mode_does_not_copy_the_original_entry(hass: HomeAssistant) -> None:
    """Extra keys of the source entries stay out of the attribute unless the template adds them."""
    hass.states.async_set(
        "sensor.prices",
        "0.1",
        {
            "data": [
                {
                    "start_time": "2026-10-01T00:00:00+02:00",
                    "end_time": "2026-10-01T00:15:00+02:00",
                    "price_per_kwh": 0.1,
                },
                {
                    "start_time": "2026-10-01T00:15:00+02:00",
                    "end_time": "2026-10-01T00:30:00+02:00",
                    "price_per_kwh": 0.2,
                },
            ]
        },
    )

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Slim",
        data={
            CONF_MODE: MODE_TRANSFORM,
            CONF_NAME: "Slim",
            CONF_SOURCE_ENTITY: "sensor.prices",
            CONF_SOURCE_ATTRIBUTE: "data",
            CONF_STATE_TEMPLATE: "{{ forecast[0].value }}",
            CONF_ATTRIBUTE_TEMPLATE: "{{ item.price_per_kwh * 10 }}",
        },
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.slim")
    assert state is not None
    # `start_time` becomes `time`; end_time and price_per_kwh are not copied
    assert state.attributes["forecast"] == [
        {"time": "2026-10-01T00:00:00+02:00", "value": 1.0},
        {"time": "2026-10-01T00:15:00+02:00", "value": 2.0},
    ]
    assert state.state == "1.0"


async def test_transform_mode_template_can_bring_back_extra_fields(
    hass: HomeAssistant,
) -> None:
    """A template that returns an object can add fields (and override the time) explicitly."""
    hass.states.async_set(
        "sensor.prices",
        "0.1",
        {"data": [{"start_time": "2026-10-01T00:00:00+02:00", "end_time": "x", "p": 1}]},
    )

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Extra",
        data={
            CONF_MODE: MODE_TRANSFORM,
            CONF_NAME: "Extra",
            CONF_SOURCE_ENTITY: "sensor.prices",
            CONF_SOURCE_ATTRIBUTE: "data",
            CONF_STATE_TEMPLATE: "{{ forecast[0].value }}",
            CONF_ATTRIBUTE_TEMPLATE: "{{ {'value': item.p, 'end_time': item.end_time} }}",
        },
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.extra")
    assert state is not None
    assert state.attributes["forecast"] == [
        {"time": "2026-10-01T00:00:00+02:00", "value": 1, "end_time": "x"}
    ]
