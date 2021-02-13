"""Climate platform for Traeger grills"""

import logging

from homeassistant.components.climate import (
    ClimateEntity,
)
from homeassistant.components.climate.const import (
    SUPPORT_TARGET_TEMPERATURE,
    HVAC_MODE_HEAT,
    HVAC_MODE_COOL,
    HVAC_MODE_OFF,
)
from homeassistant.const import (
    ATTR_TEMPERATURE,
    TEMP_CELSIUS,
    TEMP_FAHRENHEIT,
)

from .const import (
    DEFAULT_NAME,
    DOMAIN,
    GRILL_MODE_OFFLINE,
    GRILL_MODE_COOL_DOWN,
    GRILL_MODE_CUSTOM_COOK,
    GRILL_MODE_MANUAL_COOK,
    GRILL_MODE_PREHEATING,
    GRILL_MODE_IGNITING,
    GRILL_MODE_IDLE,
    GRILL_MODE_SLEEPING,
)

from .entity import IntegrationBlueprintEntity
from .traeger import traeger


async def async_setup_entry(hass, entry, async_add_devices):
    """Setup climate platform."""
    client = hass.data[DOMAIN][entry.entry_id]
    grills = client.get_grills()
    for grill in grills:
        async_add_devices([TraegerClimateEntity(client, grill["thingName"])])


class TraegerClimateEntity(ClimateEntity, IntegrationBlueprintEntity):
    """Climate entity for Traeger grills"""

    def __init__(self, client, grill_id):
        self.grill_id = grill_id
        self.client = client
        self.grill_details = None
        self.grill_state = None
        self.grill_units = None
        self.grill_limits = None

        # Tell the Traeger client to call grill_update() when it gets an update
        self.client.set_callback_for_grill(self.grill_id, self.grill_update)

    def grill_update(self):
        """This gets called when the grill has an update. Update state variable"""
        self.grill_details = self.client.get_details_for_device(self.grill_id)
        self.grill_state = self.client.get_state_for_device(self.grill_id)
        self.grill_units = self.client.get_units_for_device(self.grill_id)
        self.grill_limits = self.client.get_limits_for_device(self.grill_id)

        # Tell HA we have an update
        self.schedule_update_ha_state()

    # Generic Properties
    @property
    def name(self):
        """Return the name of the grill"""
        if self.grill_details is None:
            return f"{self.grill_id}"
        return self.grill_details["friendlyName"]

    @property
    def unique_id(self):
        return self.grill_id

    @property
    def icon(self):
        return "mdi:grill"

    # Climate Properties
    @property
    def temperature_unit(self):
        if self.grill_units == TEMP_CELSIUS:
            return TEMP_CELSIUS
        else:
            return TEMP_FAHRENHEIT

    @property
    def current_temperature(self):
        if self.grill_state is None:
            return 0
        return self.grill_state["grill"]

    @property
    def target_temperature(self):
        if self.grill_state is None:
            return 0
        return self.grill_state["set"]

    @property
    def max_temp(self):
        if self.grill_limits is None:
            return self.min_temp
        return self.grill_limits["max_grill_temp"]

    @property
    def min_temp(self):
        # this was the min the traeger app would let me set
        if self.grill_units == TEMP_CELSIUS:
            return 75
        else:
            return 165

    @property
    def hvac_mode(self):
        """Return hvac operation ie. heat, cool mode.
        Need to be one of HVAC_MODE_*.
        """
        if self.grill_state is None:
            return HVAC_MODE_OFF

        state = self.grill_state["system_status"]

        if state == GRILL_MODE_COOL_DOWN:  # Cool Down
            return HVAC_MODE_COOL
        elif state == GRILL_MODE_CUSTOM_COOK:  # Custom Cook
            return HVAC_MODE_HEAT
        elif state == GRILL_MODE_MANUAL_COOK:  # Manual Cook
            return HVAC_MODE_HEAT
        elif state == GRILL_MODE_PREHEATING:  # Preheating
            return HVAC_MODE_HEAT
        elif state == GRILL_MODE_IGNITING:  # Igniting
            return HVAC_MODE_HEAT
        elif state == GRILL_MODE_IDLE:  # Idle (Power switch on, screen on)
            return HVAC_MODE_OFF
        elif state == GRILL_MODE_SLEEPING:  # Sleeping (Power switch on, screen off)
            return HVAC_MODE_OFF
        elif state == GRILL_MODE_OFFLINE:  # Offline
            return HVAC_MODE_OFF
        else:
            return HVAC_MODE_OFF

    @property
    def hvac_modes(self):
        """Return the list of available hvac operation modes.
        Need to be a subset of HVAC_MODES.
        """
        return (HVAC_MODE_HEAT, HVAC_MODE_OFF, HVAC_MODE_COOL)

    @property
    def supported_features(self):
        """Return the list of supported features for the grill"""
        return SUPPORT_TARGET_TEMPERATURE

    # Climate Methods
    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        self.client.set_temperature(self.grill_id, temperature)
