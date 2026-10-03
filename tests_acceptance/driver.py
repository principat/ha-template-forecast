"""The single seam between the Gherkin vocabulary and Home Assistant internals.

Feature files and step definitions never touch ``hass``, config entries, or
entity IDs directly - they only call methods on :class:`Driver`. If this
project is ever rebuilt on a different stack, only this file needs
reimplementing; the ``.feature`` files (and the step *names* they bind to)
stay valid as the executable specification.

Async bridging: pytest-bdd step functions are plain synchronous functions
(it has no native async-step support as of 8.1.0 - see
tests_acceptance/README.md for why). All Home Assistant interaction is async,
though, driven by the same event loop pytest-asyncio already created for the
``hass`` fixture. ``_run()``/``_settle()`` are the only place that bridges
the two: do not "fix" step functions to be ``async def`` themselves, they
will not be awaited by pytest-bdd and the coroutine will simply never run.
"""
from __future__ import annotations

import dataclasses
from datetime import timedelta
from typing import Any

import homeassistant.util.dt as dt_util
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.template_forecast.const import (
    CONF_MODE,
    CONF_NAME,
    CONF_SOURCE_ATTRIBUTE,
    CONF_SOURCE_ENTITY,
    DOMAIN,
    MODE_GENERATE,
    MODE_TRANSFORM,
)


@dataclasses.dataclass
class HelperHandle:
    """Opaque reference to a successfully created helper, by its display name."""

    entry_id: str
    entity_id: str | None
    name: str


@dataclasses.dataclass
class FlowOutcome:
    """Result of a create/reconfigure attempt - used for both happy and error paths."""

    success: bool
    errors: dict[str, str]
    description_placeholders: dict[str, str]
    handle: HelperHandle | None


class Driver:
    """Creates/edits/reads template_forecast helpers without exposing HA internals."""

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self._handles: dict[str, HelperHandle] = {}

    # ---- async bridging ---------------------------------------------------
    def _run(self, coro: Any) -> Any:
        return self.hass.loop.run_until_complete(coro)

    def _settle(self) -> None:
        self._run(self.hass.async_block_till_done())

    # ---- creation -----------------------------------------------------------
    def create_generate_helper(self, name: str, **fields: Any) -> FlowOutcome:
        """Create a Generate-mode helper. Fields not given keep their schema default."""
        return self._run(self._async_create(name, MODE_GENERATE, fields))

    def create_transform_helper(
        self, name: str, source_entity: str, **fields: Any
    ) -> FlowOutcome:
        """Create a Transform-mode helper. Fields not given keep their schema default."""
        return self._run(
            self._async_create(name, MODE_TRANSFORM, fields, source_entity=source_entity)
        )

    async def _async_create(
        self,
        name: str,
        mode: str,
        fields: dict[str, Any],
        source_entity: str | None = None,
    ) -> FlowOutcome:
        result = await self.hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await self.hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_NAME: name, CONF_MODE: mode}
        )

        if mode == MODE_TRANSFORM:
            if result["type"] != FlowResultType.FORM:
                return self._failure(result)
            result = await self.hass.config_entries.flow.async_configure(
                result["flow_id"], {CONF_SOURCE_ENTITY: source_entity}
            )

        if result["type"] == FlowResultType.FORM:
            submitted = dict(fields)
            if mode == MODE_TRANSFORM and CONF_SOURCE_ATTRIBUTE not in submitted:
                submitted.setdefault(CONF_SOURCE_ATTRIBUTE, "forecast")
            result = await self.hass.config_entries.flow.async_configure(
                result["flow_id"], submitted
            )

        if result["type"] != FlowResultType.CREATE_ENTRY:
            return self._failure(result)

        entry = result["result"]
        await self.hass.async_block_till_done()
        entity_id = er.async_get(self.hass).async_get_entity_id(
            "sensor", DOMAIN, entry.entry_id
        )
        handle = HelperHandle(entry_id=entry.entry_id, entity_id=entity_id, name=name)
        self._handles[name] = handle
        return FlowOutcome(True, {}, {}, handle)

    @staticmethod
    def _failure(result: dict[str, Any]) -> FlowOutcome:
        return FlowOutcome(
            False,
            dict(result.get("errors") or {}),
            dict(result.get("description_placeholders") or {}),
            None,
        )

    # ---- the creation form (REQ 2.2) -------------------------------------------
    def creation_form(self, mode: str) -> dict[str, Any]:
        """Open the creation form of a mode and report its fields (in display order)
        and the values they are pre-filled with."""
        return self._run(self._async_creation_form(mode))

    async def _async_creation_form(self, mode: str) -> dict[str, Any]:
        flow = self.hass.config_entries.flow
        result = await flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
        result = await flow.async_configure(
            result["flow_id"], {CONF_NAME: "Formular", CONF_MODE: mode}
        )
        if mode == MODE_TRANSFORM:
            self.hass.states.async_set("sensor.formular_quelle", "1")
            result = await flow.async_configure(
                result["flow_id"], {CONF_SOURCE_ENTITY: "sensor.formular_quelle"}
            )
        assert result["type"] == FlowResultType.FORM, result
        schema = result["data_schema"].schema
        defaults = {
            str(key): key.default() for key in schema if key.default is not vol.UNDEFINED
        }
        return {"fields": [str(key) for key in schema], "defaults": defaults}

    # ---- editing (REQ 2.5) ---------------------------------------------------
    def reconfigure(self, name: str, **fields: Any) -> FlowOutcome:
        """Drive the options flow for an already-created helper."""
        return self._run(self._async_reconfigure(name, fields))

    async def _async_reconfigure(self, name: str, fields: dict[str, Any]) -> FlowOutcome:
        handle = self._handles[name]
        entry = self.hass.config_entries.async_get_entry(handle.entry_id)
        current = {**entry.data, **entry.options}
        merged = {**current, **fields}
        # CONF_MODE/CONF_NAME/source entity aren't part of the options schema.
        merged.pop(CONF_MODE, None)
        merged.pop(CONF_NAME, None)

        result = await self.hass.config_entries.options.async_init(handle.entry_id)
        result = await self.hass.config_entries.options.async_configure(
            result["flow_id"], merged
        )
        if result["type"] != FlowResultType.CREATE_ENTRY:
            return self._failure(result)
        await self.hass.async_block_till_done()
        return FlowOutcome(True, {}, {}, handle)

    def options_flow_schema_keys(self, name: str) -> set[str]:
        """Field keys offered by the options ("Configure") form - for REQ 2.1's
        "mode can't be changed" and REQ 2.5's "everything else can" checks."""
        return self._run(self._async_options_schema_keys(name))

    async def _async_options_schema_keys(self, name: str) -> set[str]:
        handle = self._handles[name]
        result = await self.hass.config_entries.options.async_init(handle.entry_id)
        keys = {str(key) for key in result["data_schema"].schema}
        # the options flow that was just opened is left un-submitted; that's fine,
        # pytest-homeassistant-custom-component tears down all flows after the test.
        return keys

    # ---- reading state --------------------------------------------------------
    def state_of(self, name: str) -> str:
        handle = self._handles[name]
        state = self.hass.states.get(handle.entity_id)
        assert state is not None, f"entity for helper {name!r} does not exist"
        return state.state

    def forecast_of(self, name: str, target_attribute: str = "forecast") -> list[dict]:
        handle = self._handles[name]
        state = self.hass.states.get(handle.entity_id)
        assert state is not None, f"entity for helper {name!r} does not exist"
        return list(state.attributes.get(target_attribute) or [])

    def raw_stored_config(self, name: str) -> dict[str, Any]:
        """entry.data merged with entry.options - for the REQ 2.6 persistence check."""
        handle = self._handles[name]
        entry = self.hass.config_entries.async_get_entry(handle.entry_id)
        return {**entry.data, **entry.options}

    def is_still_responsive(self, name: str) -> bool:
        """The entity still exists and answers - used after deliberately
        provoking a template render error (REQ 2.4 robustness scenarios)."""
        handle = self._handles[name]
        return self.hass.states.get(handle.entity_id) is not None

    @staticmethod
    def items_from_table(datatable: list[list[str]]) -> list[dict[str, Any]]:
        """Turn a Gherkin data table into a list of dicts, coercing numeric-looking
        cell strings to int/float - Gherkin tables are always plain text, but the
        source lists these simulate normally carry real numbers, and templates
        like ``{{ value * 2 }}`` rely on that (a string would just repeat)."""
        header, *rows = datatable
        return [
            {key: Driver._coerce(cell) for key, cell in zip(header, row)} for row in rows
        ]

    @staticmethod
    def _coerce(value: str) -> Any:
        try:
            return int(value)
        except ValueError:
            pass
        try:
            return float(value)
        except ValueError:
            return value

    # ---- simulating the outside world (REQ 2.4) --------------------------------
    def set_entity_state(self, entity_id: str, state: str, attributes: dict | None = None) -> None:
        self.hass.states.async_set(entity_id, state, attributes or {})
        self._settle()

    def set_source_forecast(self, entity_id: str, attribute: str, items: list[dict]) -> None:
        current = self.hass.states.get(entity_id)
        base_state = current.state if current is not None else "unknown"
        self.hass.states.async_set(entity_id, base_state, {attribute: items})
        self._settle()

    def advance_time(self, minutes: int) -> None:
        async_fire_time_changed(self.hass, dt_util.utcnow() + timedelta(minutes=minutes))
        self._settle()

    def restart(self, name: str) -> None:
        """Simulate a Home Assistant restart by unloading and reloading the
        entry within the same hass instance. This exercises the real
        RestoreEntity/RestoreStateData machinery (the in-memory cache of the
        entity's last written state, populated continuously since it was
        first added) without the heavier cost of tearing down and rebuilding
        the whole `hass` fixture. Documented simplification, see README."""
        handle = self._handles[name]
        self._run(self.hass.config_entries.async_unload(handle.entry_id))
        self._settle()
        self._run(self.hass.config_entries.async_setup(handle.entry_id))
        self._settle()
