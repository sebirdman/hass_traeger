"""Sensor platform for Traeger."""
from homeassistant.helpers.entity import Entity
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature

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
    GRILL_MODE_SHUTDOWN,
    GRILL_MIN_TEMP_C,
    GRILL_MIN_TEMP_F,
)

from .entity import TraegerBaseEntity, TraegerGrillMonitor


async def async_setup_entry(hass, entry, async_add_devices):
    """Setup sensor platform."""
    client = hass.data[DOMAIN][entry.entry_id]
    grills = client.get_grills()
    for grill in grills:
        grill_id = grill["thingName"]
        async_add_devices([PelletSensor(client, grill["thingName"], "Pellet Level", "pellet_level")])
        async_add_devices([ValueTemperature(client, grill["thingName"], "Ambient Temperature", "ambient")])
        async_add_devices([GrillTimer(client, grill["thingName"], "Cook Timer Start", "cook_timer_start")])
        async_add_devices([GrillTimer(client, grill["thingName"], "Cook Timer End", "cook_timer_end")])
        async_add_devices([GrillState(client, grill["thingName"], "Grill State", "grill_state")])
        async_add_devices([HeatingState(client, grill["thingName"], "Heating State", "heating_state")])
        TraegerGrillMonitor(client, grill_id, async_add_devices, ProbeState)


class TraegerBaseSensor(TraegerBaseEntity):

    def __init__(self, client, grill_id, friendly_name, value):
        super().__init__(client, grill_id)
        self.value = value
        self.friendly_name = friendly_name
        self.grill_register_callback()

    # Generic Properties
    @property
    def available(self):
        """Reports unavailable when the grill is powered off"""
        if self.grill_state is None:
            return False
        else:
            return self.grill_state["connected"]

    @property
    def name(self):
        """Return the name of the grill"""
        if self.grill_details is None:
            return f"{self.grill_id} {self.friendly_name}"
        name = self.grill_details["friendlyName"]
        return f"{name} {self.friendly_name}"

    @property
    def unique_id(self):
        return f"{self.grill_id}_{self.value}"

    # Sensor Properties
    @property
    def state(self):
        return self.grill_state[self.value]


class ValueTemperature(TraegerBaseSensor):
    """Traeger Temperature Value class."""

    # Generic Properties
    @property
    def icon(self):
        return "mdi:thermometer"

    # Sensor Properties
    @property
    def unit_of_measurement(self):
        return self.grill_units


class PelletSensor(TraegerBaseSensor):
    """Traeger Pellet Sensor class."""

    # Generic Properties
    @property
    def available(self):
        """Reports unavailable when the pellet sensor is not connected"""
        if self.grill_features is None:
            return False
        else:
            return True if self.grill_features["pellet_sensor_connected"] == 1 else False

    @property
    def icon(self):
        return "mdi:gauge"

    # Sensor Properties
    @property
    def unit_of_measurement(self):
        return "%"


class GrillTimer(TraegerBaseSensor):
    """Traeger Timer class."""

    # Generic Properties
    @property
    def icon(self):
        return "mdi:timer"

    # Sensor Properties
    @property
    def unit_of_measurement(self):
        return "sec"


class GrillState(TraegerBaseSensor):
    """Traeger Grill State class.
    These states correlate with the Traeger application.
    """

    # Generic Properties
    @property
    def icon(self):
        return "mdi:grill"

    # Sensor Properties
    @property
    def state(self):

        state = self.grill_state["system_status"]

        if state == GRILL_MODE_COOL_DOWN:
            return "cool_down"
        elif state == GRILL_MODE_CUSTOM_COOK:
            return "cook_custom"
        elif state == GRILL_MODE_MANUAL_COOK:
            return "cook_manual"
        elif state == GRILL_MODE_PREHEATING:
            return "preheating"
        elif state == GRILL_MODE_IGNITING:
            return "igniting"
        elif state == GRILL_MODE_IDLE:
            return "idle"
        elif state == GRILL_MODE_SLEEPING:
            return "sleeping"
        elif state == GRILL_MODE_OFFLINE:
            return "offline"
        elif state == GRILL_MODE_SHUTDOWN:
            return "shutdown"
        else:
            return "unknown"    # Likely a new state we don't know about


class HeatingState(TraegerBaseSensor):
    """Traeger Heating State class."""

    def __init__(self, client, grill_id, friendly_name, value):
        super().__init__(client, grill_id, friendly_name, value)
        self.previous_target_temp = None
        self.previous_state = "idle"
        self.preheat_modes = [GRILL_MODE_PREHEATING, GRILL_MODE_IGNITING]
        self.cook_modes = [GRILL_MODE_CUSTOM_COOK, GRILL_MODE_MANUAL_COOK]

    # Generic Properties
    @property
    def icon(self):
        if self.state == "over_temp":
            return "mdi:fire-alert"
        else:
            return "mdi:fire"

    # Sensor Properties
    @property
    def state(self):
        if self.grill_state is None:
            return "idle"

        target_temp = self.grill_state["set"]
        grill_mode = self.grill_state["system_status"]
        current_temp = self.grill_state["grill"]
        target_changed = True if target_temp != self.previous_target_temp else False
        min_cook_temp = (
            GRILL_MIN_TEMP_C if self.grill_units == UnitOfTemperature.CELSIUS else GRILL_MIN_TEMP_F
        )
        temp_swing = 11 if self.grill_units == UnitOfTemperature.CELSIUS else 20
        low_temp = target_temp - temp_swing
        high_temp = target_temp + temp_swing

        if grill_mode in self.preheat_modes:
            if current_temp < min_cook_temp:
                state = "preheating"
            else:
                state = "heating"
        elif grill_mode in self.cook_modes:
            if self.previous_state == "heating" or self.previous_state == "preheating":
                if current_temp >= target_temp:
                    state = "at_temp"
                else:
                    state = "heating"
            elif self.previous_state == "cooling":
                if current_temp <= target_temp:
                    state = "at_temp"
                else:
                    state = "cooling"
            elif self.previous_state == "at_temp":
                if current_temp > high_temp:
                    state = "over_temp"
                elif current_temp < low_temp:
                    state = "under_temp"
                else:
                    state = "at_temp"
            elif self.previous_state == "under_temp":
                if current_temp > low_temp:
                    state = "at_temp"
                else:
                    state = "under_temp"
            elif self.previous_state == "over_temp":
                if current_temp < high_temp:
                    state = "at_temp"
                else:
                    state = "over_temp"
            # Catch all if coming from idle/unavailable
            else:
                target_changed = True

            if target_changed:
                if current_temp <= target_temp:
                    state = "heating"
                else:
                    state = "cooling"
        elif grill_mode == GRILL_MODE_COOL_DOWN:
            state = "cool_down"
        else:
            state = "idle"

        self.previous_target_temp = target_temp
        self.previous_state = state

        return state


class ProbeState(TraegerBaseSensor):

    def __init__(self, client, grill_id, sensor_id):
        super().__init__(client, grill_id, f"Probe State {sensor_id}", f"probe_state_{sensor_id}")
        self.sensor_id = sensor_id
        self.grill_accessory = self.client.get_details_for_accessory(
            self.grill_id, self.sensor_id
        )
        self.previous_target_temp = None
        self.probe_alarm = False
        self.active_modes = [GRILL_MODE_PREHEATING, GRILL_MODE_IGNITING, GRILL_MODE_CUSTOM_COOK, GRILL_MODE_MANUAL_COOK]

        # Tell the Traeger client to call grill_accessory_update() when it gets an update
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
        """Reports unavailable when the probe is not connected"""

        if (self.grill_state is None
                or self.grill_state["connected"] == False
                or self.grill_accessory is None):
            # Reset probe alarm if accessory becomes unavailable
            self.probe_alarm = False
            return False
        else:
            connected = self.grill_accessory["con"]
            # Reset probe alarm if accessory is not connected
            if not connected:
                self.probe_alarm = False
            return connected

    @property
    def unique_id(self):
        return f"{self.grill_id}_probe_state_{self.sensor_id}"

    @property
    def icon(self):
        return "mdi:thermometer"

    # Sensor Properties
    @property
    def state(self):
        if self.grill_accessory is None:
            return "idle"

        target_temp = self.grill_accessory["probe"]["set_temp"]
        probe_temp = self.grill_accessory["probe"]["get_temp"]
        target_changed = target_temp != self.previous_target_temp
        grill_mode = self.grill_state["system_status"]
        fell_out_temp = 102 if self.grill_units == UnitOfTemperature.CELSIUS else 215

        # Latch probe alarm, reset if target changed or grill leaves active modes
        if self.grill_accessory["probe"]["alarm_fired"]:
            self.probe_alarm = True
        elif ((target_changed and target_temp != 0)
                or (grill_mode not in self.active_modes)):
            self.probe_alarm = False

        if probe_temp >= fell_out_temp:
            state = "fell_out"
        elif self.probe_alarm:
            state = "at_temp"
        elif target_temp != 0 and grill_mode in self.active_modes:
            close_temp = 3 if self.grill_units == UnitOfTemperature.CELSIUS else 5
            if probe_temp + close_temp >= target_temp:
                state = "close"
            else:
                state = "set"
        else:
            self.probe_alarm = False
            state = "idle"

        self.previous_target_temp = target_temp
        return state
