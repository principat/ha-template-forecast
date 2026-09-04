"""Constants for the Template Forecast integration."""
from __future__ import annotations

DOMAIN = "template_forecast"
PLATFORMS = ["sensor"]

# Common config keys
CONF_MODE = "mode"
CONF_NAME = "name"
CONF_STATE_TEMPLATE = "state_template"
CONF_ATTRIBUTE_TEMPLATE = "attribute_template"
CONF_TARGET_ATTRIBUTE = "target_attribute"
CONF_UPDATE_INTERVAL = "update_interval_minutes"
CONF_UNIT_OF_MEASUREMENT = "unit_of_measurement"
CONF_DEVICE_CLASS = "device_class"
CONF_STATE_CLASS = "state_class"
CONF_ICON = "icon"

# Generate mode
CONF_HORIZON_STEPS = "horizon_steps"
CONF_STEP_MINUTES = "step_minutes"

# Transform mode
CONF_SOURCE_ENTITY = "source_entity"
CONF_SOURCE_ATTRIBUTE = "source_attribute"

MODE_GENERATE = "generate"
MODE_TRANSFORM = "transform"
MODES = [MODE_GENERATE, MODE_TRANSFORM]

DEFAULT_TARGET_ATTRIBUTE = "forecast"
DEFAULT_STEP_MINUTES = 60
DEFAULT_HORIZON_STEPS = 24
DEFAULT_UPDATE_INTERVAL = 15
