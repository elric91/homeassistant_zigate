"""
ZiGate platform for Zigbee lights
"""
from time import sleep
import logging
from homeassistant.components.light import (
    ATTR_BRIGHTNESS, ATTR_COLOR_TEMP, ATTR_TRANSITION, ATTR_FLASH, FLASH_LONG,
    SUPPORT_BRIGHTNESS, SUPPORT_COLOR_TEMP, SUPPORT_FLASH, SUPPORT_TRANSITION,
    Light, PLATFORM_SCHEMA)
from homeassistant.helpers.dispatcher import (dispatcher_connect, dispatcher_send)
from homeassistant.const import (CONF_NAME, CONF_ADDRESS, STATE_UNKNOWN, CONF_TYPE)
import homeassistant.helpers.config_validation as cv

import voluptuous as vol

from custom_components.zigate.const import *
from pyzigate.zgt_parameters import *

CONF_LIGHT_TYPE = 'light_type'
CONF_FADE_SPEED = 'fade_speed'
CONF_LIGHT_MANUFACTURER = 'manufacturer'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_NAME): cv.string,
    vol.Required(CONF_ADDRESS): cv.string,
    vol.Required(CONF_LIGHT_TYPE, default='white'): cv.string,
    vol.Optional(CONF_LIGHT_MANUFACTURER, default=''): cv.string,
    vol.Optional(CONF_FADE_SPEED, default=0): cv.positive_int,
})

SUPPORTED_FEATURES = (SUPPORT_BRIGHTNESS | SUPPORT_TRANSITION)

_LOGGER = logging.getLogger(__name__)

"""
Type:
 - white
 - dual-white

"""


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the ZiGate lights."""
    device = ZiGateLight(hass, config.get(CONF_NAME), config.get(CONF_ADDRESS),
                          config.get(CONF_LIGHT_TYPE), config.get(CONF_LIGHT_MANUFACTURER),
                          )
    add_devices([device])


class ZiGateLight(Light):
    """Representation of a Zigbee light as seen by the ZiGate."""
    _commands = {
        'power': '0092',
        'brightness': '0081',
        'temperature': '00C0'
    }

    def __init__(self, hass, name, addrep, light_type, manufacturer):
        """Initialize the switch."""
        self._hass = hass
        self._name = name
        self._addrep = addrep
        self._light_type = light_type
        self._attributes = {}
        self._command_address_part = "02" + addrep[:4] + "01" + addrep[4:]

        self._state = False
        self._brightness = None
        self._temperature = None
        self._available = True

        self._features = SUPPORTED_FEATURES
        if self._light_type == "dual-white":
            self._features |= SUPPORT_COLOR_TEMP

        dispatcher_connect(hass, ZGT_SIGNAL_UPDATE.format(self._addrep), self.update_attributes)

    @property
    def unique_id(self):
        """Return the ID of this light."""
        return "{}.{}".format(self.__class__, self._addrep)

    @property
    def name(self):
        """Return the name of the device if any."""
        return self._name

    @property
    def is_on(self):
        """Return true if device is on."""
        return self._state

    @property
    def brightness(self):
        """Return the brightness of this light between 0..255."""
        return self._brightness

    @property
    def xy_color(self):
        """Return the XY color value [float, float]."""
        return None

    @property
    def color_temp(self):
        """Return the CT color value in mireds."""
        return None

    @property
    def min_mireds(self):
        """Return the coldest color_temp that this light supports."""
        # Default to the Philips Hue value that HA has always assumed
        return 154

    @property
    def max_mireds(self):
        """Return the warmest color_temp that this light supports."""
        # Default to the Philips Hue value that HA has always assumed
        return 500

    @property
    def white_value(self):
        """Return the white value of this light between 0..255."""
        return None

    @property
    def state_attributes(self):
        """Return optional state attributes."""
        data = {}

        return data

    @property
    def supported_features(self):
        """Flag supported features."""
        return self._features

    @staticmethod
    def _dec2hex_str(value):
        return "{0:0{1}x}".format(value, 2)

    @staticmethod
    def _convert_brightness(value):
        brightness_step = 255
        scaled_brightness = round(brightness_step*(value/100))
        return "{0:0{1}x}".format(scaled_brightness + 256, 4)

    def turn_on(self, **kwargs):
        """Turns light on"""
        command_sent = False
        if ATTR_BRIGHTNESS in kwargs:
            self._brightness = kwargs[ATTR_BRIGHTNESS]
            self._hass.services.call('zigate', 'raw_command', {
                'cmd': self._commands['brightness'],
                'data': self._command_address_part + '01' + self._dec2hex_str(self._brightness) + '0000'
            })
            command_sent = True

        if ATTR_COLOR_TEMP in kwargs:
            self._temperature = kwargs[ATTR_COLOR_TEMP]
            self._hass.services.call('zigate', 'raw_command', {
                'cmd': self._commands['temperature'],
                'data': self._command_address_part + self._convert_brightness(self._temperature) + '0000'
            })
            command_sent = True

        if not command_sent:
            self._hass.services.call('zigate', 'raw_command', {
                'cmd': self._commands['power'],
                'data': self._command_address_part + '01'
            })
        self._state = True
        pass

    def turn_off(self, **kwargs):
        """Turns light off"""
        self._hass.services.call('zigate', 'raw_command', {
            'cmd': self._commands['power'],
            'data': self._command_address_part + '00'
        })
        self._state = False
        pass

    def update_attributes(self, property_id, property_data):
        _LOGGER.debug("Property update: {0}: {1}", property_id, property_data)
