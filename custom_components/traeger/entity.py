"""TraegerBaseEntity class"""
from homeassistant.helpers.entity import Entity

from .const import DOMAIN, NAME, VERSION, ATTRIBUTION

class TraegerBaseEntity(Entity):

    def __init__(self, client, grill_id):
        super().__init__()
        self.grill_id = grill_id
        self.client = client
        self.grill_refresh_state()

    def grill_refresh_state(self):
        self.grill_state = self.client.get_state_for_device(self.grill_id)
        self.grill_units = self.client.get_units_for_device(self.grill_id)
        self.grill_details = self.client.get_details_for_device(self.grill_id)
        self.grill_features = self.client.get_features_for_device(self.grill_id)
        self.grill_settings = self.client.get_settings_for_device(self.grill_id)
        self.grill_limits = self.client.get_limits_for_device(self.grill_id)
        self.grill_cloudconnect = self.client.get_cloudconnect(self.grill_id)

    def grill_register_callback(self):
        # Tell the Traeger client to call grill_update() when it gets an update
        self.client.set_callback_for_grill(self.grill_id, self.grill_update_internal)

    def grill_update_internal(self):
        self.grill_refresh_state()

        if self.hass is None:
            return

        # Tell HA we have an update
        self.schedule_update_ha_state()

    @property
    def unique_id(self):
        """Return a unique ID to use for this entity."""
        return self.grill_id

    @property
    def should_poll(self):
        return False

    @property
    def device_info(self):

        if self.grill_settings is None:
            return {
                "identifiers": {(DOMAIN, self.grill_id)},
                "name": NAME,
                "manufacturer": NAME
            }

        return {
            "identifiers": {(DOMAIN, self.grill_id)},
            "name": self.grill_details["friendlyName"],
            "model": self.grill_settings["device_type_id"],
            "sw_version": self.grill_settings["fw_version"],
            "manufacturer": NAME
        }

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return {
            "attribution": ATTRIBUTION,
            "integration": DOMAIN,
        }

class TraegerGrillMonitor:
    def __init__(self, client, grill_id, async_add_devices, probe_entity = None):
        self.client = client
        self.grill_id = grill_id
        self.async_add_devices = async_add_devices
        self.probe_entity = probe_entity
        self.accessory_status = {}

        self.device_state = self.client.get_state_for_device(self.grill_id)
        self.grill_add_accessories()
        self.client.set_callback_for_grill(self.grill_id, self.grill_monitor_internal)

    def grill_monitor_internal(self):
        self.device_state = self.client.get_state_for_device(self.grill_id)
        self.grill_add_accessories()

    def grill_add_accessories(self):
        if self.device_state is None:
            return
        for accessory in self.device_state["acc"]:
            if accessory["type"] in ["probe", "btprobe", "hob"]:
                if accessory["uuid"] not in self.accessory_status:
                    if self.probe_entity:
                        self.async_add_devices([self.probe_entity(self.client, self.grill_id, accessory["uuid"])])
                        self.accessory_status[accessory["uuid"]] = True
