from cobs import cobs
from crc import Calculator, Crc16
import struct
import serial
import click


class PACKETS:
    GET_FW_VERSION = b"\x00\x02"
    GET_MAC_ADDRESS = b"\x03"
    GET_SENSOR_DATA = b"\x02"
    GET_CONFIG = b"\x01\x00"
    SET_CONFIG = b"\x01\x01"
    RESP_CONFIG_OK = b"\x00\x01\x01"  # Config set successfully
    # Format: Header, Payload
    DFU_START = {"header": b"\x00\x00", "payload_fmt": "<LH"}
    DFU_BLOCK = b"\x00\x01"



def read_packet(ser: serial.Serial):
    encoded = ser.read_until(b"\0")
    decoded = cobs.decode(encoded[:-1])
    if encoded == b"":
        raise serial.SerialTimeoutException
    return decoded

def encode_payload(header: bytes, payload_raw: bytes | None = None):
    """Given the header and raw bytes, returns a payload ready to be sent."""
    crc_calc = Calculator(Crc16.GSM)
    raw_payload = header + payload_raw if payload_raw is not None else header
    raw_payload = raw_payload + struct.pack("<H", crc_calc.checksum(raw_payload))
    return cobs.encode(raw_payload) + b"\0"


def read_fw_version(port, timeout=1):
    with serial.Serial(port, 460800, timeout=timeout) as ser:
        ser.write(encode_payload(PACKETS.GET_FW_VERSION))
        fw_version = click.style(read_packet(ser).decode("ascii"), fg="blue", bold=True)
        return fw_version