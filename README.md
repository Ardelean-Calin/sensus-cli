## To check out the documentation, please go to [this page](https://sensus.klausen.tech?source=Github)

### Install

This command-line application can be used to update, configure and log data from Sensus. 
To run this command-line application, you will need to have [**pipx**](https://github.com/pypa/pipx) installed.

Simply run this command to install `sensus-cli`:
```
pipx install git+https://github.com/Ardelean-Calin/sensus-cli.git
```

Then, to list the available commands, simply type

```
sensus --help
```

![Sensus-Help](img/sensus-help.png)

### Updating Sensus
To update the firmware, simply run:
```
sensus update --port <YOUR_SERIAL_PORT>
```

Optionally, you can force an update by specifying a .hex file:

```
sensus update --port <YOUR_SERIAL_PORT> --hex <sensus_hex_file>.hex
```
