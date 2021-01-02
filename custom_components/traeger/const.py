"""Constants for traeger."""
# Base component constants
NAME = "Traeger"
DOMAIN = "traeger"
DOMAIN_DATA = f"{DOMAIN}_data"
VERSION = "0.0.2"
ATTRIBUTION = ""
ISSUE_URL = "https://github.com/sebirdman/hass_traeger/issues"

# Icons
ICON = "mdi:format-quote-close"

# Platforms
WATER_HEATER = "water_heater"
SENSOR = "sensor"
PLATFORMS = [WATER_HEATER, SENSOR]

# Configuration and options
CONF_ENABLED = "enabled"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"

# Defaults
DEFAULT_NAME = DOMAIN


STARTUP_MESSAGE = f"""
-------------------------------------------------------------------
{NAME}
Version: {VERSION}
This is a custom integration!
If you have any issues with this you need to open an issue here:
{ISSUE_URL}
-------------------------------------------------------------------
"""
