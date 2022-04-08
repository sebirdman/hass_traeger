"""Climate platform for Traeger grills"""
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
    DOMAIN,
    GRILL_MODE_OFFLINE,
    GRILL_MODE_COOL_DOWN,
    GRILL_MODE_CUSTOM_COOK,
    GRILL_MODE_MANUAL_COOK,
    GRILL_MODE_PREHEATING,
    GRILL_MODE_IGNITING,
    GRILL_MODE_IDLE,
    GRILL_MODE_SLEEPING,
    GRILL_MIN_TEMP_C,
    GRILL_MIN_TEMP_F,
)

from .entity import TraegerBaseEntity, TraegerGrillMonitor


async def async_setup_entry(hass, entry, async_add_devices):
    """Setup climate platform."""
    client = hass.data[DOMAIN][entry.entry_id]
    grills = client.get_grills()
    for grill in grills:
        grill_id = grill["thingName"]
        async_add_devices([TraegerClimateEntity(client, grill_id, "Climate")])
        TraegerGrillMonitor(client, grill_id, async_add_devices, AccessoryTraegerClimateEntity)


class TraegerBaseClimate(ClimateEntity, TraegerBaseEntity):
    def __init__(self, client, grill_id, friendly_name):
        super().__init__(client, grill_id)
        self.friendly_name = friendly_name

    # Generic Properties
    @property
    def name(self):
        """Return the name of the grill"""
        if self.grill_details is None:
            return f"{self.grill_id} {self.friendly_name}"
        name = self.grill_details["friendlyName"]
        return f"{name} {self.friendly_name}"

    # Climate Properties
    @property
    def temperature_unit(self):
        if self.grill_units == TEMP_CELSIUS:
            return TEMP_CELSIUS
        else:
            return TEMP_FAHRENHEIT

    @property
    def target_temperature_step(self):
        return 5

    @property
    def supported_features(self):
        """Return the list of supported features for the grill"""
        return SUPPORT_TARGET_TEMPERATURE


class TraegerClimateEntity(TraegerBaseClimate):
    """Climate entity for Traeger grills"""

    def __init__(self, client, grill_id, friendly_name):
        super().__init__(client, grill_id, friendly_name)
        self.grill_register_callback()

    @property
    def unique_id(self):
        return f"{self.grill_id}_climate"

    @property
    def icon(self):
        return "mdi:grill"

    @property
    def available(self):
        """Reports unavailable when the grill is powered off"""
        if self.grill_state is None:
            return False
        else:
            return self.grill_state["connected"]

    # Climate Properties
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
        if self.grill_units == TEMP_CELSIUS:
            return GRILL_MIN_TEMP_C
        else:
            return GRILL_MIN_TEMP_F

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

    # Climate Methods
    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        await self.client.set_temperature(self.grill_id, round(temperature))

    async def async_set_hvac_mode(self, hvac_mode):
        """Start grill shutdown sequence"""
        if hvac_mode == HVAC_MODE_OFF or hvac_mode == HVAC_MODE_COOL:
            await self.client.shutdown_grill(self.grill_id)


class AccessoryTraegerClimateEntity(TraegerBaseClimate):
    """Climate entity for Traeger grills"""

    def __init__(self, client, grill_id, sensor_id):
        super().__init__(client, grill_id, f"Probe {sensor_id}")
        self.sensor_id = sensor_id
        self.grill_accessory = self.client.get_details_for_accessory(
            self.grill_id, self.sensor_id
        )

        # Tell the Traeger client to call grill_update() when it gets an update
        self.client.set_callback_for_grill(self.grill_id, self.grill_accessory_update)

    def grill_accessory_update(self):
        """This gets called when the grill has an update. Update state variable"""
        self.grill_refresh_state()
        self.grill_accessory = self.client.get_details_for_accessory(
            self.grill_id, self.sensor_id
        )

        if self.hass is None:
            return

        # Tell HA we have an update
        self.schedule_update_ha_state()

    # Generic Properties
    @property
    def available(self):
        """Reports unavailable when the grill is powered off"""
        if self.grill_state is None:
            return False
        else:
            return True if self.grill_state["probe_con"] == 1 else False

    @property
    def unique_id(self):
        return f"{self.grill_id}_probe_{self.sensor_id}"

    @property
    def icon(self):
        return "mdi:thermometer"

    # Climate Properties
    @property
    def current_temperature(self):
        if self.grill_accessory is None:
            return 0
        return self.grill_accessory["probe"]["get_temp"]

    @property
    def target_temperature(self):
        if self.grill_accessory is None:
            return 0
        return self.grill_accessory["probe"]["set_temp"]

    @property
    def max_temp(self):
        # this was the max the traeger would let me set
        if self.grill_units == TEMP_CELSIUS:
            return 100
        else:
            return 215

    @property
    def min_temp(self):
        # this was the min the traeger would let me set
        if self.grill_units == TEMP_CELSIUS:
            return 45
        else:
            return 115

    @property
    def hvac_mode(self):
        """Return hvac operation ie. heat, cool mode.
        Need to be one of HVAC_MODE_*.
        """
        if self.grill_state is None:
            return HVAC_MODE_OFF

        state = self.grill_state["probe_con"]

        if state == 1:  # Probe Connected
            return HVAC_MODE_HEAT
        else:
            return HVAC_MODE_OFF

    @property
    def hvac_modes(self):
        """Return the list of available hvac operation modes.
        Need to be a subset of HVAC_MODES.
        """
        return (HVAC_MODE_HEAT, HVAC_MODE_OFF)

    # Climate Methods
    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        await self.client.set_probe_temperature(self.grill_id, round(temperature))

    async def async_set_hvac_mode(self, hvac_mode):
        """Start grill shutdown sequence"""
        if hvac_mode == HVAC_MODE_OFF or hvac_mode == HVAC_MODE_COOL:
            hvac_mode = hvac_mode
            #await self.client.shutdown_grill(self.grill_id)
