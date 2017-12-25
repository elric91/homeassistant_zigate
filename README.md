# Custom components for Home Assistant
Custom components for Home Assistant

## Component : Rotel TCP (roteltcp.py)
A subtype of media_player that can be used through HASS to :
- turn on and off the amplifier
- adjust volume
- change source
- check status

Example minimal config (in configuration.yaml, dummy IP to be updated) :
```
media_player:
  - platform: roteltcp
    host: 192.168.1.12
```
### Component ZiGate : Zigate interface
### /!\ Ongoing Development. No pratical use yet (except for devs) /!\
