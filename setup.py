from setuptools import setup

setup(
    name="sensus-cli",
    version="0.1.0",
    py_modules=["sensus"],
    install_requires=[
        "Click",
        "Pyserial",
        "Cobs",
        "Crc",
        "python-dateutil",
        "tomli",
        "tomli-w",
        "intelhex",
    ],
    entry_points={
        "console_scripts": [
            "sensus = sensus:cli",
        ],
    },
)
