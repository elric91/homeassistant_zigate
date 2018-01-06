"""
Demo platform that has a couple of fake sensors.

For more details about this platform, please refer to the documentation
https://home-assistant.io/components/demo/
"""
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.config_validation import PLATFORM_SCHEMA
from homeassistant.helpers.dispatcher import (dispatcher_connect, dispatcher_send)
from custom_components.zigate.const import *
from homeassistant.const import (CONF_NAME, CONF_ADDRESS, STATE_UNKNOWN)
import homeassistant.helpers.config_validation as cv

import voluptuous as vol

CONF_DEFAULT_ATTR = 'default_state'
CONF_DEFAULT_UNIT = 'default_unit'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_NAME): cv.string,
    vol.Required(CONF_ADDRESS): cv.string,
    vol.Optional(CONF_DEFAULT_ATTR, default=None): cv.string,
    vol.Optional(CONF_DEFAULT_UNIT, default=None): cv.string,
})



def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the ZiGate sensors."""
    def add_new_sensor(name, address, default_addr=None, default_unit=None):
        device = ZiGateSensor(hass, name, address, default_addr, default_unit)
        add_devices([device])

    dispatcher_connect(hass, ZGT_SIGNAL_NEW_DEVICE, add_new_sensor)
    add_new_sensor(config.get(CONF_NAME), config.get(CONF_ADDRESS), 
                   config.get(CONF_DEFAULT_ATTR), config.get(CONF_DEFAULT_UNIT)
                   )


class ZiGateSensor(Entity):
    """Representation of a Demo sensor."""

    def __init__(self, hass, name, addr, default_attr=None, default_unit=None):
        """Initialize the sensor."""
        self._name = name
        self._addr = addr
        self._default_attr = default_attr
        self._default_unit = default_unit
        self._attributes = {}
        dispatcher_connect(hass, ZGT_SIGNAL_UPDATE.format(self._addr), self.update_attributes)

    @property
    def should_poll(self):
        """No polling needed for a demo sensor."""
        return False

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._attributes.get(self._default_attr, STATE_UNKNOWN)

    @property
    def unit_of_measurement(self):
        return self._attributes.get(self._default_unit, None)

    @property
    def state_attributes(self):
        """Return the state attributes."""
        return self._attributes

    def update_attributes(self, property_id, property_data):
        self._attributes[property_id] = property_data
        self.schedule_update_ha_state()


