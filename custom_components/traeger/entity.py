"""BlueprintEntity class"""
from homeassistant.helpers.entity import Entity

from .const import DOMAIN, NAME, VERSION, ATTRIBUTION


class IntegrationBlueprintEntity(Entity):

    @property
    def unique_id(self):
        """Return a unique ID to use for this entity."""
        return self.grill_id

    @property
    def should_poll(self):
        return False

    @property
    def device_info(self):
        settings = self.client.get_settings_for_device(self.grill_id)
        details = self.client.get_details_for_device(self.grill_id)

        if settings is None:
            return {
                "identifiers": {(DOMAIN, self.grill_id)},
                "name": NAME,
                "manufacturer": NAME
            }

        return {
            "identifiers": {(DOMAIN, self.grill_id)},
            "name": details["friendlyName"],
            "model": settings["device_type_id"],
            "sw_version": settings["fw_version"],
            "manufacturer": NAME
        }

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return {
            "attribution": ATTRIBUTION,
            "integration": DOMAIN,
        }
