"""Constants for traeger."""
# Base component constants
NAME = "Traeger"
DOMAIN = "traeger"
DOMAIN_DATA = f"{DOMAIN}_data"
VERSION = "0.1.0"
ATTRIBUTION = ""
ISSUE_URL = "https://github.com/sebirdman/hass_traeger/issues"

# Icons
ICON = "mdi:format-quote-close"

# Platforms
CLIMATE = "climate"
SENSOR = "sensor"
SWITCH = "switch"
NUMBER = "number"
PLATFORMS = [CLIMATE, SENSOR, SWITCH, NUMBER]

# Configuration and options
CONF_ENABLED = "enabled"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"

# Defaults
DEFAULT_NAME = DOMAIN

# Grill Modes
GRILL_MODE_OFFLINE = 99     # Offline
GRILL_MODE_SHUTDOWN = 9     # Cooled down, heading to sleep
GRILL_MODE_COOL_DOWN = 8    # Cool down cycle
GRILL_MODE_CUSTOM_COOK = 7  # Custom cook
GRILL_MODE_MANUAL_COOK = 6  # Manual cook
GRILL_MODE_PREHEATING = 5   # Preheating
GRILL_MODE_IGNITING = 4     # Igniting
GRILL_MODE_IDLE = 3         # Idle (Power switch on, screen on)
GRILL_MODE_SLEEPING = 2     # Sleeping (Power switch on, screen off)

# Grill Temps
# these are the min temps the traeger app would set
GRILL_MIN_TEMP_C = 75
GRILL_MIN_TEMP_F = 165

STARTUP_MESSAGE = f"""
-------------------------------------------------------------------
{NAME}
Version: {VERSION}
This is a custom integration!
If you have any issues with this you need to open an issue here:
{ISSUE_URL}
-------------------------------------------------------------------
"""
