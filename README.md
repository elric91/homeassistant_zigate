# ZiGate components for Home Assistant
A new component which enable to grab Zigbee data through the ZiGate (http://zigate.fr)

To install, simply copy all the files in your hass configuration folder, under 'custom\_components' and adapt your configuration.yaml


To pair a new device, go in developer/services (the little remote in the menu) and call the 'zigate.permit\_join' service.
You have 30 seconds to pair your device. If successull, you should have a notification on your home page

Example config for a xiaomi\_aqara temperature sensor :
- __address is on 6 bytes : 4 corresponding to short\_address and 2 to the endpoint\_id__
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
    address: a1b201
    default_state: temperature
    default_unit: '°C'

  - platform: template
    sensors:
      pressure1:
        friendly_name: 'LivingRoom Atmospheric Pressure'
        unit_of_measurement: 'mb'
        value_template: '{{ states.sensor.livingroom_sensor.attributes.pressure }}'

switch:
  - platform: zigate
    name: 'Presence detection'
    address: c3d401
    default_state: 'event'
```
