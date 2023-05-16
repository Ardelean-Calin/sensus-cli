from setuptools import setup, find_packages

setup(
    name="sensus-cli",
    version="0.1.0",
    packages=find_packages(),
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
            "sensus = sensus.sensus:cli",
        ],
    },
)
