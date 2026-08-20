"""Config- und Options-Flow für Template Forecast."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import CONF_UNIT_OF_MEASUREMENT
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.template import Template

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
    DOMAIN,
    MODE_GENERATE,
    MODE_TRANSFORM,
)

_NONE_OPTION = selector.SelectOptionDict(value="", label="—")


def _device_class_selector() -> selector.SelectSelector:
    options = [_NONE_OPTION] + [
        selector.SelectOptionDict(value=c.value, label=c.value)
        for c in SensorDeviceClass
    ]
    return selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=options, mode=selector.SelectSelectorMode.DROPDOWN
        )
    )


def _state_class_selector() -> selector.SelectSelector:
    options = [_NONE_OPTION] + [
        selector.SelectOptionDict(value=c.value, label=c.value)
        for c in SensorStateClass
    ]
    return selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=options, mode=selector.SelectSelectorMode.DROPDOWN
        )
    )


def _common_schema(defaults: dict[str, Any]) -> dict:
    """Felder, die in beiden Modi vorkommen.

    Templates bewusst als einfache Strings (nicht selector.TemplateSelector):
    der TemplateSelector validiert bereits auf Voluptuous-Schema-Ebene und wirft
    dabei eine harte Exception, bevor async_step_* überhaupt läuft - das würde
    _validate_templates() umgehen und dem Nutzer einen Absturz statt eines
    Formularfehlers zeigen.
    """
    return {
        vol.Required(
            CONF_STATE_TEMPLATE, default=defaults.get(CONF_STATE_TEMPLATE, "")
        ): str,
        vol.Required(
            CONF_ATTRIBUTE_TEMPLATE, default=defaults.get(CONF_ATTRIBUTE_TEMPLATE, "")
        ): str,
        vol.Optional(
            CONF_TARGET_ATTRIBUTE,
            default=defaults.get(CONF_TARGET_ATTRIBUTE, DEFAULT_TARGET_ATTRIBUTE),
        ): str,
        vol.Optional(
            CONF_UNIT_OF_MEASUREMENT,
            default=defaults.get(CONF_UNIT_OF_MEASUREMENT, ""),
        ): str,
        vol.Optional(
            CONF_DEVICE_CLASS,
            default=defaults.get(CONF_DEVICE_CLASS, ""),
        ): _device_class_selector(),
        vol.Optional(
            CONF_STATE_CLASS,
            default=defaults.get(CONF_STATE_CLASS, ""),
        ): _state_class_selector(),
        vol.Optional(
            CONF_ICON,
            default=defaults.get(CONF_ICON, ""),
        ): selector.IconSelector(),
        vol.Optional(
            CONF_UPDATE_INTERVAL,
            default=defaults.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL),
        ): vol.All(vol.Coerce(int), vol.Range(min=1)),
    }


def _generate_schema(defaults: dict[str, Any]) -> vol.Schema:
    fields = {
        vol.Optional(
            CONF_HORIZON_STEPS,
            default=defaults.get(CONF_HORIZON_STEPS, DEFAULT_HORIZON_STEPS),
        ): vol.All(vol.Coerce(int), vol.Range(min=1, max=500)),
        vol.Optional(
            CONF_STEP_MINUTES,
            default=defaults.get(CONF_STEP_MINUTES, DEFAULT_STEP_MINUTES),
        ): vol.All(vol.Coerce(int), vol.Range(min=1)),
    }
    fields.update(_common_schema(defaults))
    return vol.Schema(fields)


def _transform_schema(defaults: dict[str, Any]) -> vol.Schema:
    fields = {
        vol.Required(
            CONF_SOURCE_ATTRIBUTE,
            default=defaults.get(CONF_SOURCE_ATTRIBUTE, ""),
        ): str,
    }
    fields.update(_common_schema(defaults))
    return vol.Schema(fields)


def _validate_templates(hass, user_input: dict[str, Any]) -> dict[str, str]:
    """Templates syntaktisch prüfen, ohne die tatsächlichen Variablen zu kennen."""
    errors: dict[str, str] = {}
    for key in (CONF_STATE_TEMPLATE, CONF_ATTRIBUTE_TEMPLATE):
        value = user_input.get(key, "")
        if not value:
            continue
        template = Template(value, hass)
        try:
            template.ensure_valid()
        except Exception:  # noqa: BLE001
            errors[key] = "invalid_template"
    return errors


class TemplateForecastConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Anlegen eines neuen Template-Forecast-Helfers."""

    VERSION = 1

    def __init__(self) -> None:
        self._mode: str | None = None
        self._name: str | None = None
        self._source_entity: str | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Erster Schritt: Name + Modus wählen."""
        errors: dict[str, str] = {}
        if user_input is not None:
            self._mode = user_input[CONF_MODE]
            self._name = user_input[CONF_NAME]
            if self._mode == MODE_TRANSFORM:
                return await self.async_step_transform_source()
            return await self.async_step_generate()

        schema = vol.Schema(
            {
                vol.Required(CONF_NAME): str,
                vol.Required(CONF_MODE, default=MODE_GENERATE): vol.In(
                    {
                        MODE_GENERATE: "Generate – Werte über einen Planungshorizont erzeugen",
                        MODE_TRANSFORM: "Transform – bestehenden Forecast-Sensor transformieren",
                    }
                ),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_transform_source(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Nur im Transform-Modus: Quell-Entität separat abfragen."""
        errors: dict[str, str] = {}
        if user_input is not None:
            self._source_entity = user_input[CONF_SOURCE_ENTITY]
            return await self.async_step_transform()

        schema = vol.Schema(
            {
                vol.Required(CONF_SOURCE_ENTITY): selector.EntitySelector(),
            }
        )
        return self.async_show_form(
            step_id="transform_source", data_schema=schema, errors=errors
        )

    async def async_step_generate(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = _validate_templates(self.hass, user_input)
            if not errors:
                data = {CONF_MODE: MODE_GENERATE, CONF_NAME: self._name, **user_input}
                return self.async_create_entry(title=self._name, data=data)

        return self.async_show_form(
            step_id="generate",
            data_schema=_generate_schema(user_input or {}),
            errors=errors,
        )

    async def async_step_transform(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = _validate_templates(self.hass, user_input)
            if not errors:
                data = {
                    CONF_MODE: MODE_TRANSFORM,
                    CONF_NAME: self._name,
                    CONF_SOURCE_ENTITY: self._source_entity,
                    **user_input,
                }
                return self.async_create_entry(title=self._name, data=data)

        return self.async_show_form(
            step_id="transform",
            data_schema=_transform_schema(user_input or {}),
            errors=errors,
            description_placeholders={"source_entity": self._source_entity or ""},
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> "TemplateForecastOptionsFlow":
        return TemplateForecastOptionsFlow(config_entry)


class TemplateForecastOptionsFlow(config_entries.OptionsFlow):
    """Nachträgliches Bearbeiten eines bestehenden Helfers.

    Der Modus (Generate/Transform) steht nach dem Anlegen fest, da er die
    grundlegende Berechnungslogik bestimmt. Alle übrigen Felder inkl. der
    Quell-Entität im Transform-Modus bleiben änderbar.
    """

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    def _current(self) -> dict[str, Any]:
        return {**self._config_entry.data, **self._config_entry.options}

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        current = self._current()
        mode = current.get(CONF_MODE, MODE_GENERATE)
        errors: dict[str, str] = {}

        if user_input is not None:
            errors = _validate_templates(self.hass, user_input)
            if not errors:
                return self.async_create_entry(title="", data=user_input)

        if mode == MODE_TRANSFORM:
            schema_fields = {
                vol.Required(
                    CONF_SOURCE_ENTITY, default=current.get(CONF_SOURCE_ENTITY)
                ): selector.EntitySelector(),
            }
            schema_fields.update(_transform_schema(user_input or current).schema)
            schema = vol.Schema(schema_fields)
        else:
            schema = _generate_schema(user_input or current)

        return self.async_show_form(
            step_id="init", data_schema=schema, errors=errors
        )
