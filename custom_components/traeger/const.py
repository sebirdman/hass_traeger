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
CLIMATE = "climate"
SENSOR = "sensor"
PLATFORMS = [CLIMATE, SENSOR]

# Configuration and options
CONF_ENABLED = "enabled"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"

# Defaults
DEFAULT_NAME = DOMAIN

# Grill Modes
GRILL_MODE_OFFLINE = 99
GRILL_MODE_COOL_DOWN = 8
GRILL_MODE_CUSTOM_COOK = 7
GRILL_MODE_MANUAL_COOK = 6
GRILL_MODE_PREHEATING = 5
GRILL_MODE_IGNITING = 4
GRILL_MODE_IDLE = 3
GRILL_MODE_SLEEPING = 2

STARTUP_MESSAGE = f"""
-------------------------------------------------------------------
{NAME}
Version: {VERSION}
This is a custom integration!
If you have any issues with this you need to open an issue here:
{ISSUE_URL}
-------------------------------------------------------------------
"""
