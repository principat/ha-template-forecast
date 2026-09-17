"""Config and options flow for Template Forecast."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import CONF_UNIT_OF_MEASUREMENT
from homeassistant.core import callback
from homeassistant.data_entry_flow import SectionConfig, section
from homeassistant.helpers import selector
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
    DOMAIN,
    MODE_GENERATE,
    MODE_TRANSFORM,
)

_NONE_OPTION = selector.SelectOptionDict(value="", label="—")


class _LenientTemplateSelector(selector.TemplateSelector):
    """Renders like TemplateSelector but doesn't reject invalid syntax itself.

    The stock TemplateSelector validates the Jinja syntax as part of the
    voluptuous schema. Home Assistant's HTTP layer for config flows
    (``FlowManagerResourceView.post``) does catch that as an ``InvalidData``
    error and turns it into a per-field error, so it's not fatal in the UI -
    but it's a generic, untranslated message, and it bypasses our own
    ``errors`` dict (so it doesn't use the localized ``invalid_template``
    string). It's also fatal when a flow is driven directly, as our tests do
    via ``hass.config_entries.flow.async_configure()``, which skips that HTTP
    catch entirely. Syntax is checked separately by ``_validate_templates``
    so both paths get a consistent, localized error.
    """

    def __call__(self, data: Any) -> str:
        return str(data)


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


def _info_section_key(field: str, mode: str) -> str:
    """Key for the collapsed info/example section shown above a template field."""
    return f"{field}_info_{mode}"


def _info_section() -> section:
    """An empty, collapsed section used only to display its description text."""
    return section(vol.Schema({}), SectionConfig(collapsed=True))


_INFO_SECTION_PREFIXES = ("state_template_info_", "attribute_template_info_")


def strip_info_sections(user_input: dict[str, Any]) -> dict[str, Any]:
    """Drop the empty info-section placeholders before validating/persisting."""
    return {
        key: value
        for key, value in user_input.items()
        if not key.startswith(_INFO_SECTION_PREFIXES)
    }


def _common_schema(defaults: dict[str, Any], mode: str) -> dict:
    """Fields that appear in both modes."""
    return {
        vol.Optional(
            _info_section_key(CONF_STATE_TEMPLATE, mode), default={}
        ): _info_section(),
        vol.Required(
            CONF_STATE_TEMPLATE, default=defaults.get(CONF_STATE_TEMPLATE, "")
        ): _LenientTemplateSelector(),
        vol.Optional(
            _info_section_key(CONF_ATTRIBUTE_TEMPLATE, mode), default={}
        ): _info_section(),
        vol.Required(
            CONF_ATTRIBUTE_TEMPLATE, default=defaults.get(CONF_ATTRIBUTE_TEMPLATE, "")
        ): _LenientTemplateSelector(),
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
    fields.update(_common_schema(defaults, MODE_GENERATE))
    return vol.Schema(fields)


def _transform_schema(defaults: dict[str, Any]) -> vol.Schema:
    fields = {
        vol.Required(
            CONF_SOURCE_ATTRIBUTE,
            default=defaults.get(CONF_SOURCE_ATTRIBUTE, ""),
        ): str,
    }
    fields.update(_common_schema(defaults, MODE_TRANSFORM))
    return vol.Schema(fields)


def _validate_templates(
    hass, user_input: dict[str, Any], mode: str
) -> tuple[dict[str, str], dict[str, str]]:
    """Check templates syntactically, then with a representative test render.

    The syntax check alone can't catch a template that references a variable
    only available in the other mode (e.g. ``item`` in generate mode) - that
    only surfaces once Jinja actually evaluates it. So after the syntax
    check passes, each template is rendered once with the same shape of
    variables the sensor provides at runtime, and any render failure is
    reported on that field instead of failing silently later.

    Returns (errors, description_placeholders).
    """
    errors: dict[str, str] = {}
    placeholders: dict[str, str] = {}

    state_template_value = user_input.get(CONF_STATE_TEMPLATE, "")
    attribute_template_value = user_input.get(CONF_ATTRIBUTE_TEMPLATE, "")

    for key, value in (
        (CONF_STATE_TEMPLATE, state_template_value),
        (CONF_ATTRIBUTE_TEMPLATE, attribute_template_value),
    ):
        if not value:
            continue
        try:
            Template(value, hass).ensure_valid()
        except Exception:  # noqa: BLE001
            errors[key] = "invalid_template"

    if errors:
        return errors, placeholders

    if attribute_template_value:
        if mode == MODE_TRANSFORM:
            attribute_variables = {"index": 0, "item": {"value": 0}, "value": 0}
        else:
            horizon_steps = user_input.get(CONF_HORIZON_STEPS, DEFAULT_HORIZON_STEPS)
            attribute_variables = {
                "index": 0,
                "horizon": horizon_steps,
                "forecast_time": dt_util.utcnow(),
            }
        try:
            Template(attribute_template_value, hass).async_render(
                attribute_variables, parse_result=True
            )
        except Exception as err:  # noqa: BLE001
            errors[CONF_ATTRIBUTE_TEMPLATE] = "attribute_template_render_error"
            placeholders["attribute_template_error"] = str(err)

    if state_template_value:
        dummy_item = {"time": dt_util.utcnow().isoformat(), "value": 0}
        state_variables: dict[str, Any] = {"forecast": [dummy_item]}
        if mode == MODE_TRANSFORM:
            state_variables["source"] = None
            state_variables["source_forecast"] = [dummy_item]
        try:
            Template(state_template_value, hass).async_render(
                state_variables, parse_result=False
            )
        except Exception as err:  # noqa: BLE001
            errors[CONF_STATE_TEMPLATE] = "state_template_render_error"
            placeholders["state_template_error"] = str(err)

    return errors, placeholders


class TemplateForecastConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Create a new Template Forecast helper."""

    VERSION = 1

    def __init__(self) -> None:
        self._mode: str | None = None
        self._name: str | None = None
        self._source_entity: str | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """First step: choose name + mode."""
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
                        MODE_GENERATE: "Generate – produce values over a planning horizon",
                        MODE_TRANSFORM: "Transform – transform an existing forecast sensor",
                    }
                ),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_transform_source(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Transform mode only: ask for the source entity separately."""
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
        placeholders: dict[str, str] = {}
        if user_input is not None:
            user_input = strip_info_sections(user_input)
            errors, placeholders = _validate_templates(
                self.hass, user_input, MODE_GENERATE
            )
            if not errors:
                data = {CONF_MODE: MODE_GENERATE, CONF_NAME: self._name, **user_input}
                return self.async_create_entry(title=self._name, data=data)

        return self.async_show_form(
            step_id="generate",
            data_schema=_generate_schema(user_input or {}),
            errors=errors,
            description_placeholders=placeholders,
        )

    async def async_step_transform(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        errors: dict[str, str] = {}
        placeholders: dict[str, str] = {}
        if user_input is not None:
            user_input = strip_info_sections(user_input)
            errors, placeholders = _validate_templates(
                self.hass, user_input, MODE_TRANSFORM
            )
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
            description_placeholders={
                "source_entity": self._source_entity or "",
                **placeholders,
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> "TemplateForecastOptionsFlow":
        return TemplateForecastOptionsFlow()


class TemplateForecastOptionsFlow(config_entries.OptionsFlowWithReload):
    """Subsequent editing of an existing helper.

    The mode (Generate/Transform) is fixed once created, since it determines
    the underlying calculation logic. All other fields, including the source
    entity in transform mode, remain editable.

    Inheriting from OptionsFlowWithReload means the config entry is
    automatically reloaded when this flow finishes with changed options, so
    the integration doesn't need its own update listener for that.
    """

    def _current(self) -> dict[str, Any]:
        return {**self.config_entry.data, **self.config_entry.options}

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        current = self._current()
        mode = current.get(CONF_MODE, MODE_GENERATE)
        errors: dict[str, str] = {}
        placeholders: dict[str, str] = {}

        if user_input is not None:
            user_input = strip_info_sections(user_input)
            errors, placeholders = _validate_templates(self.hass, user_input, mode)
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
            step_id="init",
            data_schema=schema,
            errors=errors,
            description_placeholders=placeholders,
        )
