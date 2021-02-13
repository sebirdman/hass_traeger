"""Sensor platform for Traeger."""
import logging

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
                async_add_devices(
                    [AccessoryTemperatureSensor(client, grill_id, accessory["uuid"])]
                )

        async_add_devices([ValueTemperature(client, grill["thingName"], "grill")])
        async_add_devices([ValueTemperature(client, grill["thingName"], "ambient")])
        async_add_devices([PelletSensor(client, grill["thingName"], "pellet_level")])


class ValueTemperature(IntegrationBlueprintEntity):
    """Traeger Temperature Value class."""

    def __init__(self, client, grill_id, value):
        self.grill_id = grill_id
        self.client = client
        self.value = value
        self.grill_state = None
        self.grill_units = None

        # Tell the Traeger client to call grill_update() when it gets an update
        self.client.set_callback_for_grill(self.grill_id, self.grill_update)

    def grill_update(self):
        self.grill_state = self.client.get_state_for_device(self.grill_id)
        self.grill_units = self.client.get_units_for_device(self.grill_id)

        # Tell HA we have an update
        self.schedule_update_ha_state()

    # Generic Properties
    @property
    def available(self):
        """Reports unavailable when the grill is powered off"""
        if self.grill_state is None:
            return False
        else:
            return True if self.grill_state["connected"] == True else False

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{self.value.capitalize()} Temperature"

    @property
    def unique_id(self):
        return f"{self.grill_id}-{self.value}"

    @property
    def icon(self):
        return "mdi:thermometer"

    # Sensor Properties
    @property
    def state(self):
        if self.grill_state is None:
            return 0
        return self.grill_state[self.value]

    @property
    def unit_of_measurement(self):
        return self.grill_units


class AccessoryTemperatureSensor(IntegrationBlueprintEntity):
    """Traeger Temperature Accessory class."""

    def __init__(self, client, grill_id, sensor_id):
        self.grill_id = grill_id
        self.client = client
        self.sensor_id = sensor_id
        self.grill_state = None
        self.grill_units = None
        self.grill_details = None
        self.grill_accessory = None

        # Tell the Traeger client to call grill_update() when it gets an update
        self.client.set_callback_for_grill(self.grill_id, self.grill_update)

    def grill_update(self):
        self.grill_state = self.client.get_state_for_device(self.grill_id)
        self.grill_units = self.client.get_units_for_device(self.grill_id)
        self.grill_details = self.client.get_details_for_device(self.grill_id)
        self.grill_accessory = self.client.get_details_for_accessory(
            self.grill_id, self.sensor_id
        )

        # Tell HA we have an update
        self.schedule_update_ha_state()

    # Generic Properties
    @property
    def available(self):
        """Reports unavailable when the grill is powered off"""
        if self.grill_state is None:
            return False
        else:
            return True if self.grill_state["connected"] == True else False

    @property
    def name(self):
        """Return the name of the sensor."""
        if self.grill_details is None:
            return f"{self.grill_id}-{self.sensor_id}"

        name = self.grill_details["friendlyName"]
        return f"{name}-{self.sensor_id}"

    @property
    def unique_id(self):
        return f"{self.grill_id}-{self.sensor_id}"

    @property
    def icon(self):
        return "mdi:thermometer"

    # Sensor Properties
    @property
    def state(self):
        if self.grill_accessory is None:
            return 0
        return self.grill_accessory["probe"]["get_temp"]

    @property
    def unit_of_measurement(self):
        return self.grill_units
