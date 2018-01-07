# Custom components for Home Assistant
Custom components for Home Assistant

## Component : Rotel TCP (roteltcp.py)
A media_player platform that can be used through HASS to :
- turn on and off the amplifier
- adjust volume
- change source
- check status

To install, copy rotel.py in your hass configuration folder, under 'custom_components'
i.e. /home/user/.homeassistant/custom_components/rotel.py

Example minimal config (in configuration.yaml, dummy IP to be updated) :
```
media_player:
  - platform: roteltcp
    host: 192.168.1.12
```
## Component ZiGate : ZiGate interface
### /!\ still beta stage ... for developpers /!\
A new component which enable to grab Zigbee data through the ZiGate (http://zigate.fr)

To install, copy the following files in your hass configuration folder, under 'custom\_components':
- zigate/\_\_init\_\_.py
- zigate/const.py
- sensor/zigate.py
- switch/zigate.py

Grab interface.py from https://github.com/elric91/ZiGate/blob/master/interface.py and add it :
- zigate/interface.py

To pair a new device, go in developer/services (the little remote in the menu) and call the 'zigate.permit\_join' service.
You have 30 seconds to pair your device. If successull, you should have a notification on your home page

Example config for a xiaomi_aqara temperature sensor :
- temperature is registered as the default value for the sensor (which grabs temperature, pressure & humidity). Any attribute declared for the sensor can be chosen as default attribute
- pressure is made available in the interface / history / graphs through a template
- address is the short address of the Zigbee component (previously registered)

```
# Enable ZiGate
zigate:

# Add sensor (previously registered with the ZiGate)
sensor:
  - platform: zigate
    name: 'LivingRoom Sensor'
    address: a1b2
    default_state: temperature
    default_unit: '°C'

  - platform: template
    sensors:
      pressure1:
        friendly_name: "LivingRoom Atmospheric Pressure"
        entity_id: sensor.livingroom_sensor
        unit_of_measurement: 'mb'
        value_template: "{{states.sensor.livingroom_sensor.attributes.pressure}}"
```
