import math
import struct
import click
import serial
import sys
from cobs import cobs
from intelhex import IntelHex
import requests
import tempfile

from sensus.util import util

# Define the page size in bytes
PAGE_SIZE = 4096
# Must be a power of two; NOTE: if I set a block size >= 128,
# I need to serialize the length as [128, 1] instead of just [128] for some reason
BLOCK_SIZE = 64
FRAMES_PER_PAGE = math.ceil(PAGE_SIZE / BLOCK_SIZE)


def create_header(binary_size):
    number_of_blocks = int(binary_size / BLOCK_SIZE)

    payload = struct.pack("<LH", binary_size, number_of_blocks)
    return payload


def frame_generator(pages):
    for page in pages:
        for i in range(0, PAGE_SIZE, BLOCK_SIZE):
            yield page[i : i + BLOCK_SIZE]


# A generator for all DFU frames
def get_block_dict(pages):
    block_dict = {}
    for i, frame in enumerate(frame_generator(pages)):
        payload = struct.pack(f"<HB{BLOCK_SIZE}B", i, BLOCK_SIZE, *frame)
        block_dict[i] = payload
    return block_dict


@click.command()
@click.option(
    "--port",
    required=True,
    type=click.Path(),
    help="Serial port of Sensus (ex. /dev/ttyUSB0)",
)
@click.option(
    "--hex",
    type=click.Path(exists=True),
    required=False,
    help=".hex file containing firmware to be flashed",
)
@click.option(
    "--force",
    is_flag=True,
    show_default=True,
    default=False,
    help="Force updating to the latest version found online.",
)
def update(port, hex, force):
    """Update Sensus firmware via USB"""
    if hex is not None:
        # Doesn't matter what Firmware Version we have, we should always be able to flash it.
        # Create an instance of the IntelHex class with the input file name
        ih = IntelHex(hex)
    else:
        # Get the latest HEX from Github
        response = requests.get(
            "https://api.github.com/repos/ardelean-calin/sensus-fw/releases/latest"
        )
        latest_tag = response.json()["tag_name"]
        current_version = util.read_fw_version(port)
        if (latest_tag == current_version) and (force != True):
            click.echo(
                "Did not update. You are already at the latest firmware version: ",
                nl=False,
            )
            click.secho(f"{current_version}", bold=True, fg="green")
            raise click.Abort()
        # Else, download the latest hex
        click.secho("Your sensus needs updating:")
        click.echo(f"{'Current firmware version':28}", nl=False)
        click.secho(f"{current_version}", fg="yellow", bold=True)
        click.echo(f"{'Latest firmware version':28}", nl=False)
        click.secho(f"{latest_tag}", fg="green", bold=True)
        url = f"https://github.com/Ardelean-Calin/sensus-fw/releases/latest/download/sensus_{latest_tag}.hex"
        response = requests.get(url)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".hex") as f:
            f.write(response.content)
            temp_file_name = f.name

        ih = IntelHex(temp_file_name)

    # Get the start and end address of the data in the HEX file
    start_addr, end_addr = ih.minaddr(), ih.maxaddr()

    # Initialize the page address and data variables
    addresses = range(start_addr, end_addr + 1, PAGE_SIZE)
    pages = [bytes(ih[addr : addr + PAGE_SIZE].tobinarray()) for addr in addresses]
    pages[-1] = pages[-1].ljust(PAGE_SIZE, b"\0")
    dfu_header = create_header(len(pages) * PAGE_SIZE)
    blocks = get_block_dict(pages)

    to_send = util.encode_payload(b"\x00\x00", dfu_header)
    current_index = 0
    errors = 0
    with serial.Serial(port, 460800) as ser:
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        ser.write(to_send)
        with click.progressbar(length=len(blocks), label="Updating Firmware...") as bar:
            while True:
                data_encoded = ser.read_until(b"\0")
                data = cobs.decode(data_encoded[:-1])

                if data[0] == 0:
                    # Block Request
                    if data[2] == 1:
                        (current_index,) = struct.unpack("<H", data[3:5])
                        errors = 0
                        bar.update(1)
                    #  DFU Done signal
                    elif data[2] == 0:
                        break
                else:
                    errors += 1

                if errors > 3:
                    click.secho("Error during DFU.", fg="red")
                    sys.exit(0)
                # Else the current index remains, and the packet needs to be repeated.
                block = blocks[current_index]
                # block_str = " ".join(f'{x:02X}' for x in list(block))
                # print(f"Sending block: {' '.join(f'{x:02X}' for x in list(block))}")
                to_send = util.encode_payload(b"\x00\x01", block)
                ser.write(to_send)

        # DFU Done
        click.secho("DFU Done! Waiting for reset...", fg="green")

    for i in range(20):
        click.secho(f"Attempting to connect to Sensus... [Attempt {i+1} of {20}]")
        try:
            new_version = util.read_fw_version(port)
            click.secho(f"Successfully updated to  {new_version}", fg="green")
            break
        except serial.SerialTimeoutException:
            pass
