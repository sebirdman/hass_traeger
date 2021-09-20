"""Switch platform for Traeger."""
import logging

from homeassistant.components.switch import SwitchEntity

from .const import (
    DEFAULT_NAME,
    DOMAIN,
    GRILL_MODE_CUSTOM_COOK,
    GRILL_MODE_IGNITING,
)

from .entity import IntegrationBlueprintEntity
from .traeger import traeger


async def async_setup_entry(hass, entry, async_add_devices):
    """Setup Switch platform."""
    client = hass.data[DOMAIN][entry.entry_id]
    grills = client.get_grills()
    for grill in grills:
        grill_id = grill["thingName"]
        #await client.update_state(grill_id)
        state = client.get_state_for_device(grill_id)
        if state is None:
            return
        state = client.get_features_for_device(grill_id)
        if state is None:
            return
        if state["super_smoke_enabled"]:
            async_add_devices([TraegerSwitchEntity(client, grill["thingName"], "smoke", "mdi:weather-fog", 20, 21)])
        async_add_devices([TraegerSwitchEntity(client, grill["thingName"], "keepwarm", "mdi:beach", 18, 19)])
        async_add_devices([TraegerConnectEntity(client, grill["thingName"], "Connect")])

class TraegerConnectEntity(SwitchEntity, IntegrationBlueprintEntity):
    """Traeger Switch class."""

    def __init__(self, client, grill_id, devname):
        self.grill_id = grill_id
        self.client = client
        self.devname = devname
        self.grill_details = None
        self.grill_state = None
        self.grill_cloudconnect = None

        # Tell the Traeger client to call grill_update() when it gets an update
        self.client.set_callback_for_grill(self.grill_id, self.grill_update)

    def grill_update(self):
        self.grill_state = self.client.get_state_for_device(self.grill_id)
        self.grill_details = self.client.get_details_for_device(self.grill_id)
        self.grill_cloudconnect = self.client.get_cloudconnect(self.grill_id)
        
        # Tell HA we have an update
        self.schedule_update_ha_state()

    # Generic Properties
    @property
    def name(self):
        """Return the name of the grill"""
        if self.grill_details is None:
            return f"{self.grill_id}_{self.devname}"              #Returns EntID
        name = self.grill_details["friendlyName"]
        return f"{name} {self.devname.capitalize()}"              #Returns Friendly Name

    @property
    def unique_id(self):
        return f"{self.grill_id}_{self.devname}"                  #SeeminglyDoes Nothing?

    @property
    def icon(self):
        return "mdi:lan-connect"

    # Switch Properties
    @property
    def is_on(self):
        if self.grill_state is None:
            return 0
        return self.grill_cloudconnect

    # Switch Methods
    async def async_turn_on(self, **kwargs):
        """Set new Switch Val."""
        await self.client.start()

    async def async_turn_off(self, **kwargs):
        """Set new Switch Val."""
        await self.client.kill()

class TraegerSwitchEntity(SwitchEntity, IntegrationBlueprintEntity):
    """Traeger Switch class."""

    def __init__(self, client, grill_id, devname, iconinp, on_cmd, off_cmd):
        self.grill_id = grill_id
        self.client = client
        self.devname = devname
        self.iconinp = iconinp
        self.on_cmd = on_cmd
        self.off_cmd = off_cmd
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
            return f"{self.grill_id}_{self.devname}"              #Returns EntID
        name = self.grill_details["friendlyName"]
        return f"{name} {self.devname.capitalize()}"              #Returns Friendly Name

    @property
    def unique_id(self):
        return f"{self.grill_id}_{self.devname}"                  #SeeminglyDoes Nothing?

    @property
    def icon(self):
        return self.iconinp

    # Switch Properties
    @property
    def is_on(self):
        if self.grill_state is None:
            return 0
        return self.grill_state[self.devname]

    # Switch Methods
    async def async_turn_on(self, **kwargs):
        """Set new Switch Val."""
        if GRILL_MODE_IGNITING <= self.grill_state['system_status'] <= GRILL_MODE_CUSTOM_COOK:
            await self.client.set_switch(self.grill_id, self.on_cmd)

    async def async_turn_off(self, **kwargs):
        """Set new Switch Val."""
        if GRILL_MODE_IGNITING <= self.grill_state['system_status'] <= GRILL_MODE_CUSTOM_COOK:
            await self.client.set_switch(self.grill_id, self.off_cmd)
