"""
Support for ZiGate
currently only supports serial connection
(support for the wifi module will be added once serial is working properly)
"""

import asyncio
import logging
import binascii
from homeassistant.util import async as hasync
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.helpers.dispatcher import (async_dispatcher_connect, dispatcher_send)

import homeassistant.helpers.config_validation as cv
from homeassistant.const import (CONF_NAME, STATE_ON, STATE_OFF, STATE_UNKNOWN)
import voluptuous as vol
from functools import partial

from .interface import ZiGate
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
    _LOGGER.debug('ZIGATE : starting')

    # device interpreter
    zigate = Hass_ZiGate(hass)
    # initialisation of devices dict in HASS
    hass.data[DATA_ZIGATE_DEVICES] = {}
    # Asyncio serial connection to the device
    coro = serial_asyncio.create_serial_connection(hass.loop, SerialProtocol, \
                                                   config[DOMAIN].get(CONF_SERIAL_PORT), \
                                                   baudrate=config[DOMAIN].get(CONF_BAUDRATE))
    future = hasync.run_coroutine_threadsafe(coro, hass.loop)
    # bind serial connection to the device interpreter
    future.add_done_callback(partial(bind_transport_to_device, zigate))

    component = EntityComponent(_LOGGER, DOMAIN, hass)

    


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
    # temporary test functions. Will be removed later
    device.send_data("0025")


class SerialProtocol(asyncio.Protocol):

    def connection_made(self, transport):
        _LOGGER.debug('ZIGATE Transport initialized : %s' % transport)
        self.transport = transport
        transport.serial.rts = False
        #transport.write(b'hello world\n')

    def data_received(self, data):
        try:
            self.device.read_data(data)
        except:
            _LOGGER.debug('ZIGATE Data received but not ready {!r}'.format(data.decode()))

    def connection_lost(self, exc):
        _LOGGER.debug('ZIGATE Connection Lost !')


class Hass_ZiGate(ZiGate):
    def __init__(self, hass):
        super().__init__()
        self.hass = hass

    def set_device_property(self, addr, property_id, property_data):
        # decoding the address to assign the proper signal (bytes --> str)
        dispatcher_send(self.hass, ZIGATE_SIGNAL_UPDATE.format(addr.decode()), property_id, property_data)

