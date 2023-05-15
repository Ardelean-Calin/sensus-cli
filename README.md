# Sensus
Sensus is a ultra-lowpower, Homeassistant-compatible environment and plant sensor. It started as a plant health monitoring sensor but ended up being a more general-purpose environment sensor with optional addons, one of which is the Plant Health Monitoring Addon.

## Main Features
- Measures Temperature, Humidity, Illuminance and Battery Voltage
    - Additional Plant Addon also adds Soil Temperature and Soil Moisture
- **Homeassistant compatible**, plug-and-play thanks to the [BTHome data format](https://bthome.io/format/) (for more details, see https://www.home-assistant.io/integrations/bthome)
- Transmits data via Bluetooth Low Energy and USB
- Compatible with BLE4.2+ adapters
- 100m of range when transmitting data via Bluetooth
- Powered either via USB-C or a CR2032 battery
- Ultra-low power consumption, ~1 year battery life when powered from a high-quality CR2032 battery
    - Battery life can be increased (or decreased) using the command-line interface
- RGB status LED that can be used to show errors - **not yet implemented**
- [**sensus-cli**](https://github.com/Ardelean-Calin/sensus-cli) command line interface that can be used to:
    - Log real-time data via USB and save to a CSV file 
    - Log real-time data via Bluetooth and save to a CSV file - **not yet implemented**
    - Configure parameters such as time between measurements, Bluetooth name, LED behavior
    - Power-safe firmware updates
        - Update the firmware via USB
        - Update the firmware over-the-air via Bluetooth **not yet implemented**
    - Read device information such as firmware version and MAC address/serial number
- Optional magnetic 3D printed case with plexiglas window available

## How to use this command-line application
This command-line application can be used to update, configure and log data from Sensus. Installing it is as simple as running

```
python3 setup.py install
```

Then, to list the available commands, simply type

```
sensus --help
```

![Sensus-Help](img/sensus-help.png)

### Updating Sensus
To update the firmware, simply download the latest release from this Github page and then, with Sensus attached, run:

```
sensus update --port <YOUR_SERIAL_PORT> --hex sensus_<version>.hex
```