"""
Support for ZiGate
"""

import asyncio
import logging
try:
    # Valid since HomeAssistant 0.66+
    from homeassistant.util import async_ as hasync
except ImportError:
    # backwards compatibility, with workaround to avoid reserved word "async"
    # from homeassistant.util import async as hasync  # <- invalid syntax in Python 3.7
    import importlib
    hasync = importlib.import_module("homeassistant.util.async")

import homeassistant.helpers.config_validation as cv
from homeassistant.const import (CONF_NAME, CONF_HOST, CONF_PORT)
import voluptuous as vol
from functools import partial

REQUIREMENTS = ['pyserial-asyncio==0.4', 'pyzigate==0.1.3.post1']

DOMAIN = 'zigate'
COMPONENT_TYPES = ('light', 'switch', 'sensor')

_LOGGER = logging.getLogger(__name__)

CONF_BAUDRATE = 'baudrate'
CONF_SERIAL_PORT = 'serial_port'
DEFAULT_NAME = 'ZiGate'
DEFAULT_SERIAL_PORT = '/dev/ttyUSB0'
DEFAULT_BAUDRATE = 115200
DEFAULT_HOST = ''
DEFAULT_PORT = 9999
DEFAULT_CHANNEL = '11'

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
    vol.Optional(CONF_SERIAL_PORT, default=DEFAULT_SERIAL_PORT): cv.string,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_BAUDRATE, default=DEFAULT_BAUDRATE): cv.positive_int,
    vol.Optional(CONF_HOST, default=DEFAULT_HOST): cv.string,
    vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.positive_int,
    })
}, extra=vol.ALLOW_EXTRA)


@asyncio.coroutine
def async_setup(hass, config):
    """ Setup the ZiGate platform """
    import serial_asyncio
    from .zigate2hass import ZiGateProtocol, ZiGate2HASS
    from pyzigate.interface import ZiGate

    _LOGGER.debug('ZIGATE : Starting')

    # device interpreter
    zigate = ZiGate2HASS(hass)

    # Go through config and find all addresses of zigate devices
    _LOGGER.debug('ZIGATE : Finding zigate addresses')
    for domain_config in config.keys():
        if domain_config in COMPONENT_TYPES:
            for platform_config in config[domain_config]:
                if platform_config['platform'] == DOMAIN:
                    if 'address' in platform_config.keys():
                        zigate.add_known_device(str(platform_config['address'])[:4])
    _LOGGER.debug('ZIGATE : All known addresses added')

    # Commands available as HASS services
    def permit_join(call):
        """Put ZiGate in Permit Join mode and register new devices"""
        zigate.permit_join()
    
    def raw_command(call):
        """send a raw command to ZiGate"""
        cmd = call.data.get('cmd', '')
        data = call.data.get('data', '')
        zigate.send_data(cmd, data)

    def zigate_init(call):
        channel = call.data.get('channel', DEFAULT_CHANNEL)
        zigate.send_data('0021','0000%02x00' % int(channel)) # Channel
        zigate.send_data('0023','00') # Coordinator
        zigate.send_data('0024','') # Start network

    hass.services.async_register(DOMAIN, 'permit_join', permit_join)
    hass.services.async_register(DOMAIN, 'raw_command', raw_command)
    hass.services.async_register(DOMAIN, 'init', zigate_init)

    # Asyncio serial connection to the device
    # If HOST is configured, then connection is WiFi
    if config[DOMAIN].get(CONF_HOST) is "":
        # Serial
        coro = serial_asyncio.create_serial_connection(hass.loop, ZiGateProtocol, 
                                      config[DOMAIN].get(CONF_SERIAL_PORT),
                                      baudrate=config[DOMAIN].get(CONF_BAUDRATE))
    else:
        # WiFi
        coro = hass.loop.create_connection(ZiGateProtocol, 
                                           host=config[DOMAIN].get(CONF_HOST),
                                           port=config[DOMAIN].get(CONF_PORT))

    future = hasync.run_coroutine_threadsafe(coro, hass.loop)
    # bind connection to the device interpreter
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


