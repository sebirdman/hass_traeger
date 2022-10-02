"""Number/Timer platform for Traeger."""
from homeassistant.components.number import NumberEntity

from .const import (
    DOMAIN,
)

from .entity import TraegerBaseEntity

async def async_setup_entry(hass, entry, async_add_devices):
    """Setup Number/Timer platform."""
    client = hass.data[DOMAIN][entry.entry_id]
    grills = client.get_grills()
    for grill in grills:
        grill_id = grill["thingName"]
        async_add_devices([TraegerNumberEntity(client, grill["thingName"], "cook_timer")])

class TraegerNumberEntity(NumberEntity, TraegerBaseEntity):
    """Traeger Number/Timer Value class."""

    def __init__(self, client, grill_id, devname):
        super().__init__(client, grill_id)
        self.devname = devname
        self.grill_register_callback()

    # Generic Properties
    @property
    def name(self):
        """Return the name of the grill"""
        if self.grill_details is None:
            return f"{self.grill_id}_{self.devname}"
        name = self.grill_details["friendlyName"]
        return f"{name} {self.devname.capitalize()}"

    @property
    def unique_id(self):
        return f"{self.grill_id}_{self.devname}"

    @property
    def icon(self):
        return "mdi:timer"

    # Timer Properties
    @property
    def native_value(self):
        if self.grill_state is None:
            return 0
        end_time = self.grill_state[f"{self.devname}_end"]
        start_time = self.grill_state[f"{self.devname}_start"]
        tot_time = (end_time - start_time) / 60
        return tot_time

    @property
    def native_min_value(self):
        return 1

    @property
    def native_max_value(self):
        return 1440

    @property
    def native_unit_of_measurement(self):
        return "min"

    # Timer Methods
    async def async_set_native_value(self, value : float):
        """Set new Timer Val."""
        await self.client.set_timer_sec(self.grill_id, (round(value)*60))
