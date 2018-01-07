"""
Support for Rotel amplifier which can be remote controlled by tcp/ip
Known working devices :
- A14
"""

import asyncio
import logging
from homeassistant.util import async as hasync

import voluptuous as vol
from functools import partial

from homeassistant.components.media_player import (
    SUPPORT_TURN_ON, SUPPORT_TURN_OFF,
    SUPPORT_VOLUME_SET, SUPPORT_VOLUME_MUTE, SUPPORT_VOLUME_STEP,
    SUPPORT_SELECT_SOURCE,
    MediaPlayerDevice, PLATFORM_SCHEMA)

from homeassistant.const import (
    CONF_HOST, CONF_NAME, CONF_PORT, STATE_OFF, STATE_ON, STATE_UNKNOWN)
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = 'Rotel A14'
DEFAULT_PORT = 9590
DEFAULT_SOURCE = 'opt1'
CONF_SOURCE = 'source'

SUPPORT_ROTEL = SUPPORT_TURN_ON | SUPPORT_TURN_OFF | SUPPORT_SELECT_SOURCE | \
                SUPPORT_VOLUME_SET | SUPPORT_VOLUME_MUTE | SUPPORT_VOLUME_STEP 


PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_SOURCE, default=DEFAULT_SOURCE): cv.string,
})

AUDIO_SOURCES = {'phono':'Phono', 'cd':'CD', 'tuner':'Tuner', 'usb':'USB',
                 'opt1':'Optical 1', 'opt2':'Optical 2', 'coax1':'Coax 1', 'coax2':'Coax 2',
                 'bluetooth':'Bluetooth', 'pc_usb':'PC USB', 'aux1':'Aux 1', 'aux2':'Aux 2'}

AUDIO_SOURCES_SELECT = {'Phono':'phono!', 'CD':'cd!', 'Tuner':'tuner!', 'USB':'usb!',
                 'Optical 1':'opt1!', 'Optical 2':'opt2!', 'Coax 1':'coax1!', 'Coax 2':'coax2!',
                 'Bluetooth':'bluetooth!', 'PC USB':'pcusb!', 'Aux 1':'aux1!', 'Aux 2':'aux2!'}

@asyncio.coroutine
def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
    """
    Setup the Rotel platform, and the related transport
    Ask for async link as soon as transport is ready
    """
    _LOGGER.debug('ROTEL : starting')
    rotel = RotelDevice(config.get(CONF_NAME), config.get(CONF_HOST), config.get(CONF_PORT), hass.loop)
    async_add_devices([rotel])

    coro = hass.loop.create_connection(RotelProtocol, config.get(CONF_HOST), config.get(CONF_PORT))
    futur = hasync.run_coroutine_threadsafe(coro, hass.loop)
    futur.add_done_callback(partial(bind_transport_to_device, rotel))

def bind_transport_to_device(device, protocol_refs):
    """
    Bind device and protocol / transport once they are ready
    Update the device status @ start
    """
    transport = protocol_refs.result()[0]
    protocol = protocol_refs.result()[1]
    
    protocol.device = device
    device.transport = transport
    device.send_request('model?power?volume?mute?source?freq?')


class RotelDevice(MediaPlayerDevice):
    """Representation of the Rotel amplifier."""

    def __init__(self, name, host, port, loop):
        """Initialize the amplifier."""
        self._name = name
        self._host = host
        self._port = port
        self._state = None
        self._mute = None
        self._volume = '0' 
        self._source = 'phono'
        self._freq = ''
        self.msg_buffer = ''
        _LOGGER.debug("ROTEL : RotelDevice initialized")

    @property
    def name(self):
        return self._name

    @property
    def volume_level(self):
        return int(self._volume) / 100
    
    @property
    def state(self):
        if self._state == 'standby':
            return STATE_OFF
        elif self._state == 'on':
            return STATE_ON
        else:
            return STATE_UNKNOWN
   
    @property
    def is_volume_muted(self):
        if self._mute == 'on':
            return True
        else:
            return False
   
    @property
    def supported_features(self):
        return SUPPORT_ROTEL

    @property
    def media_title(self):
        if self._source in ('opt1', 'opt2'):
            return 'Playing from : %s @ %s' % (AUDIO_SOURCES[self._source], self._freq)
        else:
            return 'Playing from : %s' % AUDIO_SOURCES[self._source]

    @property
    def source_list(self):
        return list(AUDIO_SOURCES.values())
   
    @property
    def source(self):
        return AUDIO_SOURCES[self._source]

    def select_source(self, source):
        self.send_request('%s!' % AUDIO_SOURCES_SELECT[source])

    def set_volume_level(self, volume):
        self.send_request('vol_%s!' % str(round(volume * 100)).zfill(2))

    def volume_up(self):
        self.send_request('vol_up!')

    def volume_down(self):
        self.send_request('vol_dwn!')

    def mute_volume(self, mute):
        self.send_request('mute_%s!' % (mute is True and 'on' or 'off'))

    def turn_on(self):
        self.send_request('power_on!')

    def turn_off(self):
        self.send_request('power_off!')

    def data_received(self, data):
        _LOGGER.debug('DEVICE : ROTEL Data received: {!r}'.format(data.decode()))
        self.msg_buffer += data.decode() 
        commands = self.msg_buffer.split('$')
  
        # check for uncomplete commands
        if commands[-1] != '': 
            self.msg_buffer = commands[-1]
            commands.pop(-1)
        commands.pop(-1)
        # workaround for undocumented message @start
        commands = [cmd for cmd in commands if cmd[:14] != 'network_status']

        #  update statuses depending on amp messages
        for cmd in commands:
            _LOGGER.debug('DEVICE : ROTEL command %s' % cmd)
            
            action, result = cmd.split('=')
            if action == 'volume':
                self._volume = result
            elif action == 'power':
                if result == 'on/standby':
                    self.send_request('power?')
                else:
                    self._state = result
            elif action == 'mute':
                if result == 'on/off':
                    self.send_request('mute?')
                else:
                    self._mute = result
            elif action == 'source':
                self._source = result
            elif action == 'freq':
                self._freq = result

        self.async_update_ha_state()

    def send_request(self, message):
        """
        Send messages to the amp (which is a bit cheeky and may need a hard reset if command
        was not properly formatted
        """
        try:
            self.transport.write(message.encode())
            _LOGGER.debug('ROTEL Data sent: {!r}'.format(message))
        except:
            _LOGGER.debug('ROTEL : transport not ready !')


class RotelProtocol(asyncio.Protocol):

    def connection_made(self, transport):
        _LOGGER.debug('ROTEL Transport initialized')

    def data_received(self, data):
        try:
            self.device.data_received(data)
        except:
            _LOGGER.debug('ROTEL Data received but not ready {!r}'.format(data.decode()))

    def connection_lost(self, exc):
        _LOGGER.debug('ROTEL Connection Lost !')

