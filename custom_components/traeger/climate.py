"""Climate platform for Traeger grills"""
from homeassistant.components.climate import (
    ClimateEntity,
)
from homeassistant.components.climate.const import (
    SUPPORT_TARGET_TEMPERATURE,
    SUPPORT_PRESET_MODE,
    HVAC_MODE_HEAT,
    HVAC_MODE_COOL,
    HVAC_MODE_OFF,
    PRESET_NONE,
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
    GRILL_MODE_SHUTDOWN,
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

        if state == GRILL_MODE_COOL_DOWN:
            return HVAC_MODE_COOL
        elif state == GRILL_MODE_CUSTOM_COOK:
            return HVAC_MODE_HEAT
        elif state == GRILL_MODE_MANUAL_COOK:
            return HVAC_MODE_HEAT
        elif state == GRILL_MODE_PREHEATING:
            return HVAC_MODE_HEAT
        elif state == GRILL_MODE_IGNITING:
            return HVAC_MODE_HEAT
        elif state == GRILL_MODE_IDLE:
            return HVAC_MODE_OFF
        elif state == GRILL_MODE_SLEEPING:
            return HVAC_MODE_OFF
        elif state == GRILL_MODE_OFFLINE:
            return HVAC_MODE_OFF
        elif state == GRILL_MODE_SHUTDOWN:
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
        self.current_preset_mode = PRESET_NONE
        self.available_preset_modes = {
                "Chicken": {
                    TEMP_FAHRENHEIT: 165,
                    TEMP_CELSIUS: 74,
                    },
                "Turkey": {
                    TEMP_FAHRENHEIT: 165,
                    TEMP_CELSIUS: 74,
                    },
                "Beef (Rare)": {
                    TEMP_FAHRENHEIT: 125,
                    TEMP_CELSIUS: 52,
                    },
                "Beef (Medium Rare)": {
                    TEMP_FAHRENHEIT: 135,
                    TEMP_CELSIUS: 57,
                    },
                "Beef (Medium)": {
                    TEMP_FAHRENHEIT: 140,
                    TEMP_CELSIUS: 60,
                    },
                "Beef (Medium Well)": {
                    TEMP_FAHRENHEIT: 145,
                    TEMP_CELSIUS: 63,
                    },
                "Beef (Well Done)": {
                    TEMP_FAHRENHEIT: 155,
                    TEMP_CELSIUS: 68,
                    },
                "Beef (Ground)": {
                    TEMP_FAHRENHEIT: 160,
                    TEMP_CELSIUS: 71,
                    },
                "Lamb (Rare)": {
                    TEMP_FAHRENHEIT: 125,
                    TEMP_CELSIUS: 52,
                    },
                "Lamb (Medium Rare)": {
                    TEMP_FAHRENHEIT: 135,
                    TEMP_CELSIUS: 57,
                    },
                "Lamb (Medium)": {
                    TEMP_FAHRENHEIT: 140,
                    TEMP_CELSIUS: 60,
                    },
                "Lamb (Medium Well)": {
                    TEMP_FAHRENHEIT: 145,
                    TEMP_CELSIUS: 63,
                    },
                "Lamb (Well Done)": {
                    TEMP_FAHRENHEIT: 155,
                    TEMP_CELSIUS: 68,
                    },
                "Lamb (Ground)": {
                    TEMP_FAHRENHEIT: 160,
                    TEMP_CELSIUS: 71,
                    },
                "Pork (Medium Rare)": {
                    TEMP_FAHRENHEIT: 135,
                    TEMP_CELSIUS: 57,
                    },
                "Pork (Medium)": {
                    TEMP_FAHRENHEIT: 140,
                    TEMP_CELSIUS: 60,
                    },
                "Pork (Well Done)": {
                    TEMP_FAHRENHEIT: 155,
                    TEMP_CELSIUS: 68,
                    },
                "Fish": {
                    TEMP_FAHRENHEIT: 145,
                    TEMP_CELSIUS: 63,
                    },
                }

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

    @property
    def preset_mode(self):
        if (self.grill_state is None
                or self.grill_state["probe_con"] == 0
                or self.target_temperature == 0):
            # Reset current preset mode
            self.current_preset_mode = PRESET_NONE

        return self.current_preset_mode

    @property
    def preset_modes(self):
        return list(self.available_preset_modes.keys())

    @property
    def supported_features(self):
        """Return the list of supported features for the grill"""
        return SUPPORT_TARGET_TEMPERATURE | SUPPORT_PRESET_MODE

    # Climate Methods
    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        self.current_preset_mode = PRESET_NONE
        temperature = kwargs.get(ATTR_TEMPERATURE)
        await self.client.set_probe_temperature(self.grill_id, round(temperature))

    async def async_set_hvac_mode(self, hvac_mode):
        """Start grill shutdown sequence"""
        if hvac_mode == HVAC_MODE_OFF or hvac_mode == HVAC_MODE_COOL:
            hvac_mode = hvac_mode
            #await self.client.shutdown_grill(self.grill_id)

    async def async_set_preset_mode(self, preset_mode):
        """Set new target preset mode"""
        self.current_preset_mode = preset_mode
        temperature = self.available_preset_modes[preset_mode][self.grill_units]
        await self.client.set_probe_temperature(self.grill_id, round(temperature))
