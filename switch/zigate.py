"""
ZiGate platform for Zigbee switches
"""
from time import sleep
from homeassistant.components.switch import (SwitchDevice, PLATFORM_SCHEMA)
from homeassistant.helpers.dispatcher import (dispatcher_connect, dispatcher_send)
from custom_components.zigate.const import *
from homeassistant.const import (CONF_NAME, CONF_ADDRESS, STATE_UNKNOWN)
import homeassistant.helpers.config_validation as cv

import voluptuous as vol


CONF_DEFAULT_ATTR = 'default_state'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_NAME): cv.string,
    vol.Required(CONF_ADDRESS): cv.string,
    vol.Optional(CONF_DEFAULT_ATTR, default=None): cv.string,
})



def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the ZiGate sensors."""
    device = ZiGateSwitch(hass, config.get(CONF_NAME), config.get(CONF_ADDRESS), 
                         config.get(CONF_DEFAULT_ATTR)
                         )
    add_devices([device])

class ZiGateSwitch(SwitchDevice):
    """Representation of a Zigbee switch as seen by the ZiGate."""

    def __init__(self, hass, name, addr, default_attr=None):
        """Initialize the switch."""
        self._name = name
        self._addr = addr
        self._default_attr = default_attr
        self._attributes = {}
        dispatcher_connect(hass, ZGT_SIGNAL_UPDATE.format(self._addr), self.update_attributes)

    @property
    def should_poll(self):
        return False

    @property
    def name(self):
        """Return the name of the switch."""
        return self._name

    @property
    def state_attributes(self):
        """Return the state attributes."""
        return self._attributes

    def update_attributes(self, property_id, property_data):
        self._attributes[property_id] = property_data
        self.schedule_update_ha_state()
        # if the signal "event_presence" has been sent, put state to normal after 15 secs
        # No need to go async as we don't care for notifications during these 15 secs
        if property_id == ZGT_EVENT and property_data == ZGT_EVENT_PRESENCE:
            sleep(15)
            self.update_attributes(property_id, None)
    
    @property
    def is_on(self):
        """Return true if switch is on."""
        state = self._attributes.get(self._default_attr, STATE_UNKNOWN)
        if state in ZGT_SWITCH_ON_STATES:
            return True
        else:
            return False

    def turn_on(self, **kwargs):
        """Turn the switch on."""
        self._state = True
        self.schedule_update_ha_state()

    def turn_off(self, **kwargs):
        """Turn the device off."""
        # Disarm the activated event
        if self._default_attr == ZGT_EVENT:
            self._attributes[ZGT_EVENT] = None
        self._state = False
        self.schedule_update_ha_state()

