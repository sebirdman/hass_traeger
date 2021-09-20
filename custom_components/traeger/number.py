"""Number/Timer platform for Traeger."""
import logging

from homeassistant.components.number import NumberEntity

from .const import (
    DEFAULT_NAME,
    DOMAIN,
)

from .entity import IntegrationBlueprintEntity
from .traeger import traeger


async def async_setup_entry(hass, entry, async_add_devices):
    """Setup Number/Timer platform."""
    client = hass.data[DOMAIN][entry.entry_id]
    grills = client.get_grills()
    for grill in grills:
        grill_id = grill["thingName"]
        #await client.update_state(grill_id)
        state = client.get_state_for_device(grill_id)
        if state is None:
            return
        async_add_devices([TraegerNumberEntity(client, grill["thingName"], "cook_timer")])

class TraegerNumberEntity(NumberEntity, IntegrationBlueprintEntity):
    """Traeger Number/Timer Value class."""

    def __init__(self, client, grill_id, devname):
        self.grill_id = grill_id
        self.client = client
        self.devname = devname
        self.grill_details = None
        self.grill_state = None

        # Tell the Traeger client to call grill_update() when it gets an update
        self.client.set_callback_for_grill(self.grill_id, self.grill_update)

    def grill_update(self):
        self.grill_state = self.client.get_state_for_device(self.grill_id)
        self.grill_details = self.client.get_details_for_device(self.grill_id)
        
        # Tell HA we have an update
        self.schedule_update_ha_state()

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
    def value(self):
        if self.grill_state is None:
            return 0
        end_time = self.grill_state[f"{self.devname}_end"]
        start_time = self.grill_state[f"{self.devname}_start"]
        tot_time = (end_time - start_time) / 60
        return tot_time

    @property
    def min_value(self):
        return 1

    @property
    def max_value(self):
        return 1440

    @property
    def unit_of_measurement(self):
        return "min"

    # Timer Methods
    async def async_set_value(self, value : float):
        """Set new Timer Val."""
        await self.client.set_timer_sec(self.grill_id, (round(value)*60))
