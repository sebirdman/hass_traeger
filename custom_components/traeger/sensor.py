"""Sensor platform for Traeger."""
from homeassistant.helpers.entity import Entity
from homeassistant.const import ATTR_TEMPERATURE, TEMP_CELSIUS, TEMP_FAHRENHEIT

from .const import (
    DEFAULT_NAME,
    DOMAIN,
)

from .entity import TraegerBaseEntity

async def async_setup_entry(hass, entry, async_add_devices):
    """Setup sensor platform."""
    client = hass.data[DOMAIN][entry.entry_id]
    grills = client.get_grills()
    for grill in grills:
        grill_id = grill["thingName"]
        async_add_devices([PelletSensor(client, grill["thingName"], "Pellet Level",  "pellet_level")])
        async_add_devices([ValueTemperature(client, grill["thingName"], "Ambient Temperature", "ambient")])
        async_add_devices([GrillTimer(client, grill["thingName"], "Cook Timer Start", "cook_timer_start")])
        async_add_devices([GrillTimer(client, grill["thingName"], "Cook Timer End", "cook_timer_end")])


class TraegerBaseSensor(TraegerBaseEntity):

    def __init__(self, client, grill_id, friendly_name, value):
        super().__init__(client, grill_id)
        self.value = value
        self.friendly_name = friendly_name
        self.grill_register_callback()

    # Generic Properties
    @property
    def available(self):
        """Reports unavailable when the grill is powered off"""
        if self.grill_state is None:
            return False
        else:
            return self.grill_state["connected"]

    @property
    def name(self):
        """Return the name of the grill"""
        if self.grill_details is None:
            return f"{self.grill_id} {self.friendly_name}"
        name = self.grill_details["friendlyName"]
        return f"{name} {self.friendly_name}"

    @property
    def unique_id(self):
        return f"{self.grill_id}_{self.value}"

    # Sensor Properties
    @property
    def state(self):
        return self.grill_state[self.value]


class ValueTemperature(TraegerBaseSensor):
    """Traeger Temperature Value class."""

    # Generic Properties
    @property
    def icon(self):
        return "mdi:thermometer"

    # Sensor Properties
    @property
    def unit_of_measurement(self):
        return self.grill_units


class PelletSensor(TraegerBaseSensor):
    """Traeger Pellet Sensor class."""

    # Generic Properties
    @property
    def available(self):
        """Reports unavailable when the pellet sensor is not connected"""
        if self.grill_features is None:
            return False
        else:
            return True if self.grill_features["pellet_sensor_connected"] == 1 else False

    @property
    def icon(self):
        return "mdi:gauge"

    # Sensor Properties
    @property
    def unit_of_measurement(self):
        return "%"

class GrillTimer(TraegerBaseSensor):
    """Traeger Timer class."""

    # Generic Properties
    @property
    def icon(self):
        return "mdi:timer"

    # Sensor Properties
    @property
    def unit_of_measurement(self):
        return "sec"
