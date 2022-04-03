"""Binary Sensor platform for Traeger."""
from homeassistant.helpers.entity import Entity

from .const import (
    DEFAULT_NAME,
    DOMAIN,
)

from .entity import TraegerBaseEntity

async def async_setup_entry(hass, entry, async_add_devices):
    """Setup Binary Sensor platform."""
    client = hass.data[DOMAIN][entry.entry_id]
    grills = client.get_grills()
    for grill in grills:
        grill_id = grill["thingName"]
        async_add_devices([zTimer(client, grill["thingName"], "Cook Timer Complete", "cook_timer_complete")])
        async_add_devices([zProbe(client, grill["thingName"], "Probe Alarm Fired", "probe_alarm_fired")])

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

class zTimer(TraegerBaseSensor):
    """Traeger Binary class."""

    # Generic Properties
    @property
    def icon(self):
        return "mdi:timer"

class zProbe(TraegerBaseSensor):
    """Traeger Binary class."""

    # Generic Properties
    @property
    def icon(self):
        return "mdi:thermometer"
