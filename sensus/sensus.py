import click
import struct
import serial
import tomli
import time
import datetime
import enum
from datetime import timedelta
from dateutil.parser import parse
from cobs import cobs
from crc import Calculator, Crc16
from sensus import dfu
from sensus.util import util
from sensus.util.util import PACKETS, read_fw_version
from collections import namedtuple
from typing import NamedTuple

import tomli_w


class STATUSLED_POWERMODE(enum.IntEnum):
    ALWAYS = 0
    PLUGGED_IN = 1
    OFF = 2

def decode_sensor_data(data_raw: bytes):
    (
        illuminance,
        temperature,
        humidity,
        battery_voltage,
        moisture,
        soil_temp,
    ) = struct.unpack("<ffffff", data_raw)

    data = {
        "Illuminance [Lux]": round(illuminance, 2),
        "Air Temperature [°C]": round(temperature, 2),
        "Air Humidity [%]": round(humidity, 2),
        "Battery Voltage [V]": round(battery_voltage, 3),
        "Soil Moisture [%]": round(moisture, 2),
        "Soil Temperature [°C]": round(soil_temp, 2),
    }

    return data


def format_data(data: dict):
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    s = f"{current_time:^20}, "
    for v in data.values():
        entry = f"{v}"
        s += f"{entry:^20}, "
    s = s[:-2] + "\n"

    return s


def to_timestamp(value):
    try:
        dt = parse(value)
        td = timedelta(hours=dt.hour, minutes=dt.minute, seconds=dt.second)
        if int(td.total_seconds()) < 1:
            raise Exception
        return td
    except:
        raise click.BadParameter("Should be something like 20m30s or 60s")


def status_to_enum(status_str: str) -> int:
    """Converts the statuled strings `always`, `plugged-in` and `off` to their enum representations."""
    retval = None
    if status_str.lower() == "always":
        retval = STATUSLED_POWERMODE.ALWAYS
    elif status_str.lower() == "plugged-in":
        retval = STATUSLED_POWERMODE.PLUGGED_IN
    elif status_str.lower() == "off":
        retval = STATUSLED_POWERMODE.OFF
    else:
        raise Exception

    return int(retval)


def str_to_ms(time_str: str) -> int:
    """Convert a time formatted string like `1m10s` to milliseconds."""
    dt = parse(time_str)
    td = timedelta(hours=dt.hour, minutes=dt.minute, seconds=dt.second)
    return int(td.total_seconds() * 1000)


@click.group()
def cli():
    """This command-line utility can be used to log sensor data, configure and update your Sensus."""



@click.command()
@click.option(
    "--port",
    required=True,
    type=click.Path(),
    help="Serial port of the Sensus you want to update (ex. /dev/ttyUSB0)",
)
@click.option("--timeout", type=str, default="3s", help="Timeout in seconds.")
def get_fw_version(port, timeout):
    """Retrieved the current firmware version."""
    fw_version = read_fw_version(port, to_timestamp(timeout).seconds)
    click.echo(f"Firmware version:  {fw_version}")


@click.option(
    "--port",
    required=True,
    type=click.Path(),
    help="Serial port of the Sensus you want to update (ex. /dev/ttyUSB0)",
)
@click.command()
def config_get(port):
    """Retreives the current config"""
    with serial.Serial(port, 460800) as ser:
        ser.write(util.encode_payload(PACKETS.GET_CONFIG))
        result_encoded = ser.read_until(b"\0")
        result_decoded = cobs.decode(result_encoded[:-1])
        (
            onb_plugged_ms,
            probe_plugged_ms,
            onb_battery_ms,
            probe_battery_ms,
            status_led,
            size_of_name,
        ) = struct.unpack("<LLLLBB", result_decoded[3 : 3 + struct.calcsize("<LLLLBB")])
        name = result_decoded[3 + struct.calcsize("<LLLLBB") :].decode("ascii")

        # Create a dictionary which we will then convert to a TOML.
        config = {
            "general": {"name": name},
            "battery": {
                "onboard-sample-interval": f"{int(onb_battery_ms/1000)}s",
                "probe-sample-interval": f"{int(probe_battery_ms/1000)}s",
            },
            "plugged": {
                "onboard-sample-interval": f"{int(onb_plugged_ms/1000)}s",
                "probe-sample-interval": f"{int(probe_plugged_ms/1000)}s",
            },
            "statusled": {"enabled": f"{['always', 'plugged-in', 'off'][status_led]}"},
        }

        toml = tomli_w.dumps(config)
        click.echo(toml)


@click.command()
@click.option("--config", type=click.Path(exists=True), required=True)
@click.option(
    "--port",
    required=True,
    type=click.Path(),
    help="Serial port of the Sensus you want to update (ex. /dev/ttyUSB0)",
)
def config_set(config, port):
    """Configure Sensus via a TOML file"""
    with click.open_file(config, "rb") as f:
        try:
            d = tomli.load(f)
            onb_plugged_ms = str_to_ms(d["plugged"]["onboard-sample-interval"])
            probe_plugged_ms = str_to_ms(d["plugged"]["probe-sample-interval"])
            onb_battery_ms = str_to_ms(d["battery"]["onboard-sample-interval"])
            probe_battery_ms = str_to_ms(d["battery"]["probe-sample-interval"])
            status_led = status_to_enum(d["statusled"]["enabled"])

            name = d["general"]["name"]
            size_of_name = len(name)

            # Create the raw bytes from the config.toml
            payload = struct.pack(
                f"<LLLLBB{size_of_name}B",
                onb_plugged_ms,
                probe_plugged_ms,
                onb_battery_ms,
                probe_battery_ms,
                status_led,
                size_of_name,
                *bytes(name, encoding="ascii"),
            )

            with serial.Serial(port, 460800) as ser:
                ser.write(util.encode_payload(PACKETS.SET_CONFIG, payload))
                result_encoded = ser.read_until(b"\0")
                result_decoded = cobs.decode(result_encoded[:-1])

                if result_decoded == PACKETS.RESP_CONFIG_OK:
                    click.secho("Config set successfully!", bold=True, fg="green")

        except:
            raise click.BadParameter(
                f"Config file malformed. Are you sure {config} is a valid Sensus config file?"
            )


@click.command()
@click.option(
    "--port",
    required=True,
    type=click.Path(),
    help="Serial port of the Sensus you want to update (ex. /dev/ttyUSB0)",
)
@click.option(
    "--output-file",
    type=click.File("wb"),
    help="Optional CSV file to save the data to. If no file is specified, we only log to stdout.",
)
@click.option(
    "--every",
    default=None,
    type=str,
    help='Optional inverval between data reads of the form "12h34m56s". Not specifying this interval will cause only one single read.',
)
def log(port, output_file, every):
    """Start logging sensor data to file"""

    if output_file is not None:
        output_file_name = click.style(f"{output_file.name}", bold=True, fg="green")
    else:
        output_file_name = click.style("console", bold=True, fg="red")
    every_style = click.style(f"{every}", bold=True, fg="green")
    click.secho(
        f"Started logging data to {output_file_name} every {every_style}.\n",
    )
    wrote_header = False

    with serial.Serial(port, 460800) as ser:
        while True:
            start_time = datetime.datetime.now()
            ser.write(util.encode_payload(PACKETS.GET_SENSOR_DATA))
            result_encoded = ser.read_until(b"\0")
            result_decoded = cobs.decode(result_encoded[:-1])
            # Extract the sensor data
            data_raw = result_decoded[2:]
            data = decode_sensor_data(data_raw)

            # Get a CSV line
            data_line = format_data(data)
            if wrote_header is False:
                header = f"{'Time':^20}, "
                header += ", ".join([f"{key:^20}" for key in data.keys()])
                data_line = header + "\n" + data_line
                wrote_header = True

            click.echo(data_line, nl=False)
            if output_file is not None:
                output_file.write(bytes(data_line, encoding="utf-8"))
                output_file.flush()

            if every is None:
                break
            else:
                td = to_timestamp(every)
                wakeup_time = start_time + td
                time.sleep((wakeup_time - datetime.datetime.now()).total_seconds())


@click.command()
@click.option(
    "--port",
    required=True,
    type=click.Path(),
    help="Serial port of the Sensus you want to update (ex. /dev/ttyUSB0)",
)
def info(port):
    """Display information such as MAC address and FW version"""

    with serial.Serial(port, 460800) as ser:
        ser.write(util.encode_payload(PACKETS.GET_FW_VERSION))
        result_encoded = ser.read_until(b"\0")
        result_decoded = cobs.decode(result_encoded[:-1])
        # Extract the firmware version
        version = result_decoded[4:].decode("ascii")

        ser.write(util.encode_payload(PACKETS.GET_MAC_ADDRESS))
        result_encoded = ser.read_until(b"\0")
        result_decoded = cobs.decode(result_encoded[:-1])
        # Extract the MAC address
        address = ":".join(["{:02X}".format(b) for b in result_decoded[2:]])

    version_str = f"- {'Current firmware version':32}" + click.style(
        f"{':':^4}{version}", bold=True
    )
    click.echo(version_str)

    address_str = f"- {'MAC address':32}" + click.style(f"{':':^4}{address}", bold=True)
    click.echo(address_str)


cli.add_command(dfu.update)
cli.add_command(config_set)
cli.add_command(config_get)
cli.add_command(log)
cli.add_command(get_fw_version)
cli.add_command(info)
