"""
ZiGate platform for Zigbee switches
"""
from time import sleep
from homeassistant.components.switch import (SwitchDevice, PLATFORM_SCHEMA)
from homeassistant.helpers.dispatcher import (dispatcher_connect, dispatcher_send)
from homeassistant.const import (CONF_NAME, CONF_ADDRESS, STATE_UNKNOWN, CONF_TYPE)
import homeassistant.helpers.config_validation as cv

import voluptuous as vol

from custom_components.zigate.const import *
from pyzigate.zgt_parameters import *

CONF_DEFAULT_ATTR = 'default_state'
CONF_INVERTED = 'inverted'
CONF_AUTOTOGGLE_DELAY = 'autotoggle_delay'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_NAME): cv.string,
    vol.Required(CONF_ADDRESS): cv.string,
    vol.Optional(CONF_DEFAULT_ATTR, default='None'): cv.string,
    vol.Optional(CONF_TYPE, default=None): vol.Any(None,
                                                   ZGT_SWITCHTYPE_TOGGLE,
                                                   ZGT_SWITCHTYPE_MOMENTARY),
    vol.Optional(CONF_INVERTED, default=False): cv.boolean,
    vol.Optional(CONF_AUTOTOGGLE_DELAY, default=ZGT_AUTOTOGGLE_DELAY): cv.positive_int,
})

"""
types :
none : switches status on & off according with events
toggle : will swich state on 'on/pressed' events only
momentary : will switch state on 'on/pressed' and switch it back some time later

inverted :
will switch back to previous state some seconds later
"""


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the ZiGate sensors."""
    device = ZiGateSwitch(hass, config.get(CONF_NAME), config.get(CONF_ADDRESS), 
                         config.get(CONF_DEFAULT_ATTR), config.get(CONF_TYPE),
                         config.get(CONF_INVERTED), config.get(CONF_AUTOTOGGLE_DELAY)
                         )
    add_devices([device])


class ZiGateSwitch(SwitchDevice):
    """Representation of a Zigbee switch as seen by the ZiGate."""
    def __init__(self, hass, name, addrep, default_attr, switchtype, inverted, autotoggle_delay):
        """Initialize the switch."""
        self._hass = hass
        self._name = name
        self._addrep = addrep
        self._default_attr = default_attr if default_attr != 'None' else None
        self._switchtype = switchtype
        self._inverted = inverted
        self._attributes = {}
        self._state = False
        self._autotoggle_delay = autotoggle_delay
        dispatcher_connect(hass, ZGT_SIGNAL_UPDATE.format(self._addrep),
                           self.update_attributes)

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

        if self._inverted is True:
            on_states = [ZGT_STATE_OFF]
        else:
            on_states = [ZGT_EVENT_PRESENCE, ZGT_STATE_ON] 

        # update the status on / off if appropriate
        if property_id == self._default_attr:
            if property_data in on_states:
                if self._switchtype == ZGT_SWITCHTYPE_TOGGLE:
                    self._state = not self._state
                elif self._switchtype == ZGT_SWITCHTYPE_MOMENTARY:
                    # switch back state after xx secs
                    # no asyncio required as nthing expected during this time
                    self._state = True
                    self.schedule_update_ha_state()
                    sleep(self._autotoggle_delay)
                    self._state = False
                else:
                    self._state = True
            else:
                if self._switchtype == ZGT_SWITCHTYPE_TOGGLE:
                    pass
                elif self._switchtype == ZGT_SWITCHTYPE_MOMENTARY:
                    pass
                else:
                    self._state = False

        self.schedule_update_ha_state()
    
    @property
    def is_on(self):
        """Return true if switch is on."""
        return self._state

    def turn_on(self, **kwargs):
        """Turn the switch on."""
        self._state = True
        # Send the ON command
        self._hass.services.call('zigate', 'raw_command', {
            'cmd': '0092',
            'data': "02{addr}01{ep}01".format(
                addr=self._addrep[:4],
                ep=self._addrep[-2:]
            )
        })
        self.schedule_update_ha_state()

    def turn_off(self, **kwargs):
        """Turn the device off."""
        # Disarm the activated event
        if self._default_attr == ZGT_EVENT:
            self._attributes[ZGT_EVENT] = None
        self._state = False
        # Send the OFF command
        self._hass.services.call('zigate', 'raw_command', {
            'cmd': '0092',
            'data': "02{addr}01{ep}00".format(
                addr=self._addrep[:4],
                ep=self._addrep[-2:]
            )
        })
        self.schedule_update_ha_state()
