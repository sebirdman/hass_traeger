"""Switch platform for Traeger."""
from homeassistant.components.switch import SwitchEntity

from .const import (
    DOMAIN,
    GRILL_MODE_CUSTOM_COOK,
    GRILL_MODE_IGNITING,
)

from .entity import TraegerBaseEntity

async def async_setup_entry(hass, entry, async_add_devices):
    """Setup Switch platform."""
    client = hass.data[DOMAIN][entry.entry_id]
    grills = client.get_grills()
    for grill in grills:
        grill_id = grill["thingName"]
        async_add_devices([TraegerSuperSmokeEntity(client, grill["thingName"], "smoke", "Super Smoke Enabled", "mdi:weather-fog", 20, 21)])
        async_add_devices([TraegerSwitchEntity(client, grill["thingName"], "keepwarm", "Keep Warm Enabled", "mdi:beach", 18, 19)])
        async_add_devices([TraegerConnectEntity(client, grill["thingName"], "connect", "Connect")])

class TraegerBaseSwitch(SwitchEntity, TraegerBaseEntity):
    def __init__(self, client, grill_id, devname, friendly_name):
        TraegerBaseEntity.__init__(self, client, grill_id)
        self.devname = devname
        self.friendly_name = friendly_name
        self.grill_register_callback()

    # Generic Properties
    @property
    def name(self):
        """Return the name of the grill"""
        if self.grill_details is None:
            return f"{self.grill_id}_{self.devname}"              #Returns EntID
        name = self.grill_details["friendlyName"]
        return f"{name} {self.friendly_name}"              #Returns Friendly Name

    @property
    def unique_id(self):
        return f"{self.grill_id}_{self.devname}"                  #SeeminglyDoes Nothing?


class TraegerConnectEntity(TraegerBaseSwitch):
    """Traeger Switch class."""

    # Generic Properties
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
        await self.client.start(1)

    async def async_turn_off(self, **kwargs):
        """Set new Switch Val."""
        await self.client.kill()

class TraegerSwitchEntity(TraegerBaseSwitch):
    """Traeger Switch class."""

    def __init__(self, client, grill_id, devname, friendly_name, iconinp, on_cmd, off_cmd):
        super().__init__(client, grill_id, devname, friendly_name)
        self.grill_register_callback()
        self.iconinp = iconinp
        self.on_cmd = on_cmd
        self.off_cmd = off_cmd

    # Generic Properties
    @property
    def icon(self):
        return self.iconinp

    @property
    def available(self):
        if self.grill_state is None:
            return False
        else:
            if GRILL_MODE_IGNITING <= self.grill_state['system_status'] <= GRILL_MODE_CUSTOM_COOK:
                return True
        return False

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

class TraegerSuperSmokeEntity(TraegerSwitchEntity):
    """Traeger Super Smoke Switch class."""

    @property
    def available(self):
        if self.grill_state is None:
            return False
        else:
            if GRILL_MODE_IGNITING <= self.grill_state['system_status'] <= GRILL_MODE_CUSTOM_COOK:
                return True if self.grill_features["super_smoke_enabled"] == 1 else False
        return False
