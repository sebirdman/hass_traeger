"""Binary sensor platform for integration_blueprint."""
from homeassistant.components.water_heater import (
    SUPPORT_OPERATION_MODE,
    SUPPORT_TARGET_TEMPERATURE,
    WaterHeaterEntity,
)
from homeassistant.const import ATTR_TEMPERATURE, TEMP_CELSIUS, TEMP_FAHRENHEIT

from .const import (
    DEFAULT_NAME,
    DOMAIN,
)

from .entity import IntegrationBlueprintEntity
from .traeger import traeger

async def async_setup_entry(hass, entry, async_add_devices):
    """Setup water_heater platform."""
    client = hass.data[DOMAIN][entry.entry_id]
    grills = client.get_grills()
    for grill in grills:
        async_add_devices([IntegrationBlueprintBinarySensor(client, grill["thingName"])])

class IntegrationBlueprintBinarySensor(WaterHeaterEntity, IntegrationBlueprintEntity):
    """integration_blueprint binary_sensor class."""

    def grill_update(self):
        self.schedule_update_ha_state()

    def __init__(self, client, grill_id):
        self.grill_id = grill_id
        self.client = client
        self.client.set_callback_for_grill(self.grill_id, self.grill_update)

    @property
    def name(self):
        """Return the name of the binary_sensor."""
        state = self.client.get_details_for_device(self.grill_id)
        if state is None:
            return f"{self.grill_id}"
        return state["friendlyName"]

    @property
    def unique_id(self):
        return self.grill_id

    @property
    def current_temperature(self):
        state = self.client.get_state_for_device(self.grill_id)
        if state is None:
            return 0
        return state["grill"]

    @property
    def target_temperature(self):
        state = self.client.get_state_for_device(self.grill_id)
        if state is None:
            return 0
        return state["set"]

    @property
    def target_temperature_high(self):
        return self.target_temperature

    @property
    def target_temperature_low(self):
        return self.target_temperature

    @property
    def min_temp(self):
        # this was the min the traeger app would let me set
        if self.client.get_units_for_device(self.grill_id) == TEMP_CELSIUS:
            return 75
        else:
            return 165

    @property
    def max_temp(self):
        limits = self.client.get_limits_for_device(self.grill_id)
        if limits is None:
            return self.min_temp
        return limits["max_grill_temp"]

    @property
    def supported_features(self):
        """Return the list of supported features for the grill"""
        return (SUPPORT_TARGET_TEMPERATURE)

    @property
    def temperature_unit(self):
        if self.client.get_units_for_device(self.grill_id) == TEMP_CELSIUS:
            return TEMP_CELSIUS
        else:
            return TEMP_FAHRENHEIT

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        self.client.set_temperature(self.grill_id, temperature)
