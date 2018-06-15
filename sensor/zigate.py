"""
ZiGate platform for Zigbee sensors.
"""
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.config_validation import PLATFORM_SCHEMA
from homeassistant.helpers.dispatcher import (dispatcher_connect, dispatcher_send)
from homeassistant.helpers.restore_state import async_get_last_state
from homeassistant.const import (CONF_NAME, CONF_ADDRESS, STATE_UNKNOWN, ATTR_FRIENDLY_NAME)
import homeassistant.helpers.config_validation as cv

import asyncio
import logging
import voluptuous as vol

from custom_components.zigate.const import *
from pyzigate.zgt_parameters import *

_LOGGER = logging.getLogger(__name__)

CONF_DEFAULT_ATTR = 'default_state'
CONF_DEFAULT_UNIT = 'default_unit'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_NAME): cv.string,
    vol.Required(CONF_ADDRESS): cv.string,
    vol.Optional(CONF_DEFAULT_ATTR, default=''): cv.string,
    vol.Optional(CONF_DEFAULT_UNIT, default=''): cv.string,
})



def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the ZiGate sensors."""
    device = ZiGateSensor(hass, config.get(CONF_NAME), config.get(CONF_ADDRESS), 
                         config.get(CONF_DEFAULT_ATTR), config.get(CONF_DEFAULT_UNIT)
                         )
    add_devices([device])


class ZiGateSensor(Entity):
    """Representation of a Zigbee sensor as seen by the Zigate."""

    def __init__(self, hass, name, addr, default_attr=ZGT_LAST_SEEN, default_unit=None):
        """Initialize the sensor."""
        self._name = name
        self._addr = addr
        self._default_attr = default_attr if default_attr != '' else ZGT_LAST_SEEN
        self._default_unit = default_unit if default_unit != '' else None
        self._attributes = {}
        dispatcher_connect(hass, ZGT_SIGNAL_UPDATE.format(self._addr), self.update_attributes)

    @property
    def should_poll(self):
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
        return self._default_unit

    @property
    def state_attributes(self):
        """Return the state attributes."""
        return self._attributes

    def update_attributes(self, property_id, property_data):
        self._attributes[property_id] = property_data
        self.schedule_update_ha_state()


    @asyncio.coroutine
    def async_added_to_hass(self):
        """Handle entity which will be added."""
        state = yield from async_get_last_state(self.hass, self.entity_id)
        if state:
            for attr in iter(state.attributes):
                if attr != ATTR_FRIENDLY_NAME:
                    _LOGGER.info('{}: set attribute {} from last state: {}'.format(self._name, attr, state.attributes[attr]))
                    self.update_attributes(attr, state.attributes[attr])
