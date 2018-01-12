# Const for zigate
from .interface import (ZGT_TEMPERATURE, ZGT_PRESSURE, ZGT_DETAILED_PRESSURE, \
                        ZGT_HUMIDITY, ZGT_LAST_SEEN, ZGT_EVENT, ZGT_EVENT_PRESENCE, \
                        ZGT_STATE, ZGT_STATE_ON, ZGT_STATE_MULTI, ZGT_STATE_OFF, \
                        ZGT_CMD_NEW_DEVICE
                        ) 

# 1 Signal channel for each device
ZGT_SIGNAL_UPDATE = 'zgt_signal_update_{}'
ZGT_SIGNAL_NEW_DEVICE = 'zgt_signal_new_device'

# switches types
ZGT_SWITCHTYPE_TOGGLE = 'toggle'
ZGT_SWITCHTYPE_MOMENTARY = 'momentary'

ZGT_AUTOTOGGLE_DELAY = 15
