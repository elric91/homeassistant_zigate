"""
Support for ZiGate
currently only supports serial connection
(support for the wifi module will be added once serial is working properly)
"""

import asyncio
import logging
import binascii
from homeassistant.util import async as hasync
from homeassistant.helpers.dispatcher import (async_dispatcher_connect, dispatcher_send)

import homeassistant.helpers.config_validation as cv
from homeassistant.const import (CONF_NAME, STATE_ON, STATE_OFF, STATE_UNKNOWN)
import voluptuous as vol
from functools import partial

from .interface import (ZiGate, ZGT_CMD_NEW_DEVICE)
from .const import *

REQUIREMENTS = ['pyserial-asyncio==0.4']

DOMAIN = 'zigate'

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = 'ZiGate'
DEFAULT_SERIAL_PORT = '/dev/ttyUSB0'
DEFAULT_BAUDRATE = 115200
CONF_BAUDRATE = 'baudrate'
CONF_SERIAL_PORT = 'serial_port'

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
    vol.Optional(CONF_SERIAL_PORT, default=DEFAULT_SERIAL_PORT): cv.string,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_BAUDRATE, default=DEFAULT_BAUDRATE): cv.positive_int
    })
}, extra=vol.ALLOW_EXTRA)


@asyncio.coroutine
def async_setup(hass, config):
    """ Setup the ZiGate platform """
    import serial_asyncio
    _LOGGER.debug('ZIGATE : Starting')

    # device interpreter
    zigate = ZiGate2HASS(hass)
    def permit_join(call):
        """Put ZiGate in Permit Join mode and register new devices"""
        zigate.permit_join()
    
    def raw_command(call):
        """send a raw command to ZiGate"""
        cmd = call.data.get('cmd', '')
        data = call.data.get('data', '')
        zigate.send_data(cmd, data)

    hass.services.async_register(DOMAIN, 'permit_join', permit_join)
    hass.services.async_register(DOMAIN, 'raw_command', raw_command)

    # Asyncio serial connection to the device
    coro = serial_asyncio.create_serial_connection(hass.loop, SerialProtocol, \
                                                   config[DOMAIN].get(CONF_SERIAL_PORT), \
                                                   baudrate=config[DOMAIN].get(CONF_BAUDRATE))
    future = hasync.run_coroutine_threadsafe(coro, hass.loop)
    # bind serial connection to the device interpreter
    future.add_done_callback(partial(bind_transport_to_device, zigate))
    
    
    return True

def bind_transport_to_device(device, protocol_refs):
    """
    Bind device and protocol / transport once they are ready
    Update the device status @ start
    """
    transport = protocol_refs.result()[0]
    protocol = protocol_refs.result()[1]
    
    protocol.device = device
    device.send_to_transport = transport.write


class SerialProtocol(asyncio.Protocol):

    def connection_made(self, transport):
        _LOGGER.debug('ZIGATE : Transport initialized : %s' % transport)
        self.transport = transport
        transport.serial.rts = False
        #transport.write(b'hello world\n')

    def data_received(self, data):
        try:
            self.device.read_data(data)
        except:
            _LOGGER.debug('ZIGATE : Data received but not ready {!r}'.format(data.decode()))

    def connection_lost(self, exc):
        _LOGGER.debug('ZIGATE : Connection Lost !')


class ZiGate2HASS(ZiGate):
    def __init__(self, hass):
        super().__init__()
        self.hass = hass
        self.config_request_id = None

    def set_device_property(self, addr, property_id, property_data):
        # decoding the address to assign the proper signal (bytes --> str)
        dispatcher_send(self.hass, ZGT_SIGNAL_UPDATE.format(addr.decode()), property_id, property_data)

    def set_external_command(self, cmd, **kwargs):
        if cmd == ZGT_CMD_NEW_DEVICE:
            addr = kwargs['addr']
            entity_id = 'new_device_{}'.format(addr)
            current_ids = self.hass.states.async_entity_ids()
            print('ENTITY : ', entity_id)
            print('ENTITIES : ', current_ids)
            # hack on name to optimize later
            if 'sensor.{}'.format(entity_id) not in current_ids:
                dispatcher_send(self.hass, ZGT_SIGNAL_NEW_DEVICE, entity_id, addr)
                


