"""
Support for ZiGate
currently only supports serial connection
(support for the wifi module will be added once serial is working properly)
"""

import serial
import asyncio
import logging
import binascii
from homeassistant.util import async as hasync
from homeassistant.helpers.entity import Entity

import homeassistant.helpers.config_validation as cv
from homeassistant.const import (CONF_NAME)
import voluptuous as vol
from functools import partial

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
    _LOGGER.debug('ZIGATE : starting')
    
    zigate = Zigate(config[DOMAIN].get(CONF_NAME))
    coro = create_serial_connection(hass.loop, SerialProtocol, config[DOMAIN].get(CONF_SERIAL_PORT), \
                                    baudrate=config[DOMAIN].get(CONF_BAUDRATE))
    futur = hasync.run_coroutine_threadsafe(coro, hass.loop)
    futur.add_done_callback(partial(bind_transport_to_device, zigate))

    return True

def bind_transport_to_device(device, protocol_refs):
    """
    Bind device and protocol / transport once they are ready
    Update the device status @ start
    """
    transport = protocol_refs.result()[0]
    protocol = protocol_refs.result()[1]
    
    protocol.device = device
    device.transport = transport
    # temporary test functions. Will be removed later
    device.send_data("0010", "0000", "")
    device.reset()


class Zigate(Entity):
    """ Representation of the Zigate """

    def __init__(self, name):
        self._name = name
        self._state = None
        self._buffer = b''

    @property
    def name(self):
        return self._name

    def send_data(self, cmd, length, data):

        byte_cmd = bytes.fromhex(cmd)
        byte_length = bytes.fromhex(length)
        byte_data = bytes.fromhex(data)

        msg = [0x01]
        msg.extend(self.transcode(byte_cmd))
        msg.extend(self.transcode(byte_length))
        msg.append(self.checksum(byte_cmd, byte_length, byte_data))
        if data != "":
            msg.extend(self.transcode(byte_data))
        msg.append(0x03)
        # list to binary conversion
        msg = b''.join([bytes([x]) for x in msg])

        try:
            self.transport.write(msg)
            _LOGGER.debug('ZIGATE sent data : %s' % binascii.hexlify(msg))
        except:
            _LOGGER.debug('ZIGATE transport not available to send data : %s' % binascii.hexlify(msg))


    def data_received(self, data):
        self._buffer += data
        endpos = self._buffer.find(b'\x03')
        while endpos != -1:
            startpos = self._buffer.find(b'\x01')
            _LOGGER.debug('ZIGATE received data : %s' %  binascii.hexlify(self._buffer[startpos:endpos + 1]))
            #self.decode(self._buffer[startpos + 1:endpos])  # stripping starting 0x01 & ending 0x03
            self._buffer = self._buffer[endpos + 1:]
            endpos = self._buffer.find(b'\x03')

        
    @staticmethod
    def bxor_join(b1, b2):  # use xor for bytes
        parts = []
        for b1, b2 in zip(b1, b2):
            parts.append(bytes([b1 ^ b2]))
        return b''.join(parts)

    @staticmethod
    def transcode(data):
        transcoded = []
        for x in data:
            if x < 0x10:
                transcoded.append(0x02)
                transcoded.append(x ^ 0x10)
            else:
                transcoded.append(x)

        return transcoded

    @staticmethod
    def checksum(cmd, length, data):
        tmp = 0
        tmp ^= cmd[0]
        tmp ^= cmd[1]
        tmp ^= length[0]
        tmp ^= length[1]
        if data:
            for x in data:
                tmp ^= x

        return tmp

    def reset(self):
        self.send_data("0021", "0004", "00000800")  # Set Channel Mask
        self.send_data("0023", "0001", "00")  # Set Device Type [Router]
        self.send_data("0024", "0000", "")  # Start Network
        self.send_data("0049", "0004", "FFFCFE00")


class SerialProtocol(asyncio.Protocol):

    def connection_made(self, transport):
        _LOGGER.debug('ZIGATE Transport initialized : %s' % transport)
        self.transport = transport
        transport.serial.rts = False
        #transport.write(b'hello world\n')

    def data_received(self, data):
        try:
            self.device.data_received(data)
        except:
            _LOGGER.debug('ZIGATE Data received but not ready {!r}'.format(data.decode()))

    def connection_lost(self, exc):
        _LOGGER.debug('ZIGATE Connection Lost !')










###########################################################################################################
# serial aio experimental (will be replaced by the standard pyserial.aio module once stabilized)          #
# source : https://github.com/martinohanlon/microbit-micropython/blob/master/examples/mcfly/serial/aio.py #
###########################################################################################################

@asyncio.coroutine
def create_serial_connection(loop, protocol_factory, *args, **kwargs):
    ser = serial.Serial(*args, **kwargs)
    protocol = protocol_factory()
    transport = SerialTransport(loop, protocol, ser)
    return (transport, protocol)

class SerialTransport(asyncio.Transport):
    def __init__(self, loop, protocol, serial_instance):
        self._loop = loop
        self._protocol = protocol
        self.serial = serial_instance
        self._closing = False
        self._paused = False
        self.serial.timeout = 0
        self.serial.nonblocking()
        loop.call_soon(protocol.connection_made, self)
        # only start reading when connection_made() has been called
        loop.call_soon(loop.add_reader, self.serial.fd, self._read_ready)

    def __repr__(self):
        return '{self.__class__.__name__}({self._loop}, {self._protocol}, {self.serial})'.format(self=self)

    def close(self):
        if self._closing:
            return
        self._closing = True
        self._loop.remove_reader(self.serial.fd)
        self.serial.close()
        self._loop.call_soon(self._protocol.connection_lost, None)

    def _read_ready(self):
        data = self.serial.read(1024)
        if data:
            self._protocol.data_received(data)

    def write(self, data):
        self.serial.write(data)

    def can_write_eof(self):
        return False

    def pause_reading(self):
        if self._closing:
            raise RuntimeError('Cannot pause_reading() when closing')
        if self._paused:
            raise RuntimeError('Already paused')
        self._paused = True
        self._loop.remove_reader(self._sock_fd)
        if self._loop.get_debug():
            logging.debug("%r pauses reading", self)

    def resume_reading(self):
        if not self._paused:
            raise RuntimeError('Not paused')
        self._paused = False
        if self._closing:
            return
        self._loop.add_reader(self._sock_fd, self._read_ready)
        if self._loop.get_debug():
            logging.debug("%r resumes reading", self)        
