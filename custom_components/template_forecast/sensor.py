"""Sensor platform for Template Forecast."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_UNIT_OF_MEASUREMENT
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_interval,
)
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.template import Template
import homeassistant.util.dt as dt_util

from .const import (
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
    CONF_UPDATE_INTERVAL,
    DEFAULT_HORIZON_STEPS,
    DEFAULT_STEP_MINUTES,
    DEFAULT_TARGET_ATTRIBUTE,
    DEFAULT_UPDATE_INTERVAL,
    MODE_GENERATE,
    MODE_TRANSFORM,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create the helper entity from the config entry."""
    async_add_entities([TemplateForecastSensor(hass, entry)])


def _try_number(value: Any) -> Any:
    """Rendered templates return strings, but numbers should stay numbers."""
    if isinstance(value, str):
        try:
            if "." in value:
                return float(value)
            return int(value)
        except ValueError:
            return value
    return value


class TemplateForecastSensor(SensorEntity, RestoreEntity):
    """A sensor whose state and forecast attribute are computed from templates."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self._entry = entry
        self._attr_unique_id = entry.entry_id
        self._attr_name = None  # config entry title is used as the entity name
        self._unsub_state_tracking: list[Any] = []
        self._unsub_timer: Any = None
        self._attr_native_value = None
        self._attr_extra_state_attributes: dict[str, Any] = {}
        self._apply_config()

    def _config(self) -> dict[str, Any]:
        """Merge data + options (options win)."""
        return {**self._entry.data, **self._entry.options}

    def _apply_config(self) -> None:
        cfg = self._config()
        self._mode = cfg.get(CONF_MODE, MODE_GENERATE)
        self._attr_name = cfg.get(CONF_NAME)
        self._state_template = Template(cfg[CONF_STATE_TEMPLATE], self.hass)
        self._attribute_template = Template(cfg[CONF_ATTRIBUTE_TEMPLATE], self.hass)
        self._target_attribute = cfg.get(
            CONF_TARGET_ATTRIBUTE, DEFAULT_TARGET_ATTRIBUTE
        )
        unit = cfg.get(CONF_UNIT_OF_MEASUREMENT)
        self._attr_native_unit_of_measurement = unit or None

        device_class = cfg.get(CONF_DEVICE_CLASS)
        self._attr_device_class = (
            SensorDeviceClass(device_class) if device_class else None
        )

        state_class = cfg.get(CONF_STATE_CLASS)
        self._attr_state_class = (
            SensorStateClass(state_class) if state_class else None
        )

        icon = cfg.get(CONF_ICON)
        self._attr_icon = icon or None

        self._update_interval = cfg.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)

        self._horizon_steps = cfg.get(CONF_HORIZON_STEPS, DEFAULT_HORIZON_STEPS)
        self._step_minutes = cfg.get(CONF_STEP_MINUTES, DEFAULT_STEP_MINUTES)

        self._source_entity = cfg.get(CONF_SOURCE_ENTITY)
        self._source_attribute = cfg.get(CONF_SOURCE_ATTRIBUTE)

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()

        last_state = await self.async_get_last_state()
        if last_state is not None:
            self._attr_native_value = last_state.state
            self._attr_extra_state_attributes = dict(last_state.attributes)

        await self._async_recompute()
        self._async_setup_tracking()

    async def async_will_remove_from_hass(self) -> None:
        for unsub in self._unsub_state_tracking:
            unsub()
        if self._unsub_timer:
            self._unsub_timer()

    @callback
    def _async_setup_tracking(self) -> None:
        """Recompute on state changes of relevant entities + periodically."""
        entities: set[str] = set()

        for tpl in (self._state_template, self._attribute_template):
            try:
                info = tpl.async_render_to_info(self._dummy_variables())
                entities.update(info.entities)
            except Exception:  # noqa: BLE001
                _LOGGER.debug(
                    "Could not determine template dependencies for %s",
                    self.entity_id,
                )

        if self._mode == MODE_TRANSFORM and self._source_entity:
            entities.add(self._source_entity)

        if entities:
            self._unsub_state_tracking = [
                async_track_state_change_event(
                    self.hass, list(entities), self._handle_tracked_change
                )
            ]

        self._unsub_timer = async_track_time_interval(
            self.hass, self._handle_timer, timedelta(minutes=self._update_interval)
        )

    def _dummy_variables(self) -> dict[str, Any]:
        """Placeholder variables only for dependency detection (no real rendering)."""
        return {
            "index": 0,
            "horizon": self._horizon_steps,
            "forecast_time": dt_util.utcnow(),
            "item": {},
            "value": None,
            "forecast": [],
            "source": None,
            "source_forecast": [],
        }

    @callback
    def _handle_tracked_change(self, event: Event) -> None:
        self.hass.async_create_task(self._async_recompute())

    @callback
    def _handle_timer(self, now) -> None:
        self.hass.async_create_task(self._async_recompute())

    async def _async_recompute(self) -> None:
        try:
            if self._mode == MODE_GENERATE:
                forecast_list, extra_vars = self._compute_generate()
            else:
                forecast_list, extra_vars = self._compute_transform()
        except Exception:  # noqa: BLE001
            _LOGGER.exception(
                "Error computing the forecast for %s", self.entity_id
            )
            return

        state_vars = {"forecast": forecast_list, **extra_vars}
        try:
            rendered_state = self._state_template.async_render(
                state_vars, parse_result=False
            )
        except Exception:  # noqa: BLE001
            _LOGGER.exception(
                "Error rendering the state template for %s", self.entity_id
            )
            rendered_state = None

        self._attr_native_value = _try_number(rendered_state)
        self._attr_extra_state_attributes = {self._target_attribute: forecast_list}

        if self.hass is not None and self.entity_id is not None:
            self.async_write_ha_state()

    def _compute_generate(self) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        forecast_list: list[dict[str, Any]] = []
        base_time = dt_util.utcnow()

        for index in range(self._horizon_steps):
            forecast_time = base_time + timedelta(minutes=self._step_minutes * index)
            variables = {
                "index": index,
                "horizon": self._horizon_steps,
                "forecast_time": forecast_time,
            }
            value = self._attribute_template.async_render(
                variables, parse_result=False
            )
            forecast_list.append(
                {
                    "datetime": forecast_time.replace(
                        second=0, microsecond=0
                    ).isoformat(),
                    "value": _try_number(value),
                }
            )

        return forecast_list, {}

    def _compute_transform(self) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        source_state = self.hass.states.get(self._source_entity)
        source_list: list[dict[str, Any]] = []
        if source_state is not None:
            source_list = source_state.attributes.get(self._source_attribute) or []

        if not isinstance(source_list, list):
            _LOGGER.warning(
                "Attribute '%s' of %s is not a list, ignoring it",
                self._source_attribute,
                self._source_entity,
            )
            source_list = []

        forecast_list: list[dict[str, Any]] = []
        for index, item in enumerate(source_list):
            item = item if isinstance(item, dict) else {"value": item}
            variables = {
                "index": index,
                "item": item,
                "value": item.get("value"),
            }
            value = self._attribute_template.async_render(
                variables, parse_result=True
            )
            new_item = dict(item)
            if isinstance(value, dict):
                new_item.update(value)
            else:
                new_item["value"] = value
            forecast_list.append(new_item)

        extra_vars = {
            "source": source_state.state if source_state else None,
            "source_forecast": source_list,
        }
        return forecast_list, extra_vars
