"""Sensor platform for Traeger."""
from homeassistant.helpers.entity import Entity
from homeassistant.const import ATTR_TEMPERATURE, TEMP_CELSIUS, TEMP_FAHRENHEIT

from .const import (
    DEFAULT_NAME,
    DOMAIN,
)

from .entity import IntegrationBlueprintEntity


async def async_setup_entry(hass, entry, async_add_devices):
    """Setup sensor platform."""
    client = hass.data[DOMAIN][entry.entry_id]
    grills = client.get_grills()
    for grill in grills:
        grill_id = grill["thingName"]
        await client.update_state(grill_id)
        state = client.get_state_for_device(grill_id)
        if state is None:
            return
        for accessory in state["acc"]:
            if accessory["type"] == "probe":
                async_add_devices([AccessoryTemperatureSensor(
                    client, grill_id, accessory["uuid"])])

        async_add_devices(
            [ValueTemperature(client, grill["thingName"], "grill")])
        async_add_devices(
            [ValueTemperature(client, grill["thingName"], "ambient")])


class ValueTemperature(IntegrationBlueprintEntity):
    """Traeger Temperature Value class."""

    def grill_update(self):
        self.schedule_update_ha_state()

    def __init__(self, client, grill_id, value):
        self.grill_id = grill_id
        self.client = client
        self.value = value
        self.client.set_callback_for_grill(self.grill_id, self.grill_update)

    @property
    def name(self):
        """Return the name of the binary_sensor."""
        return f"{self.value.capitalize()} Temperature"

    @property
    def unique_id(self):
        return f"{self.grill_id}-{self.value}"

    @property
    def state(self):
        state = self.client.get_state_for_device(self.grill_id)
        if state is None:
            return 0
        return state[self.value]

    @property
    def unit_of_measurement(self):
        return self.client.get_units_for_device(self.grill_id)


class AccessoryTemperatureSensor(IntegrationBlueprintEntity):
    """Traeger Temperature Accessory class."""

    def grill_update(self):
        self.schedule_update_ha_state()

    def __init__(self, client, grill_id, sensor_id):
        self.grill_id = grill_id
        self.client = client
        self.sensor_id = sensor_id
        self.client.set_callback_for_grill(self.grill_id, self.grill_update)

    @property
    def name(self):
        """Return the name of the binary_sensor."""
        details = self.client.get_details_for_device(self.grill_id)
        name = details["friendlyName"]
        if details is None:
            return f"{self.grill_id}-{self.sensor_id}"
        return f"{name}-{self.sensor_id}"

    @property
    def unique_id(self):
        return f"{self.grill_id}-{self.sensor_id}"

    @property
    def state(self):
        accessory = self.client.get_details_for_accessory(
            self.grill_id, self.sensor_id)
        if accessory is None:
            return 0
        return accessory["probe"]["get_temp"]

    @property
    def unit_of_measurement(self):
        return self.client.get_units_for_device(self.grill_id)
