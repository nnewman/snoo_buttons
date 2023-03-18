# Snoo Buttons

## Why

The Snoo bassinet only has a start button, everything else is controlled via an app. If someone
is coming over to help and needs to control the bassinet, you either need to share credentials
for the app or be present to manipulate the Snoo. 

With a Raspberry Pi and some buttons, we can solve this.

## Configuration

### Required parts

- 4 buttons
- Breadboard
- Patch wires
- LED
- 330 Ohm resistor

### Wiring the breaboard

- Wire a common ground on the breadboard to the RPi ground
- Wire LED to common ground and to resistor, then connecting the resistor to a GPIO pin.
Note the pin
- Wire each button to the common ground and then to a GPIO bin. Note the pins

### Setting up the library

Tested on a Raspberry Pi with Raspian, but should work elsewhere too.

- Clone with: `git clone https://github.com/nnewman/snoo_buttons.git` and `cd snoo_buttons`
- Create `.snoo_credentials.json` with a json of your "username" and "password". This is used
once to generate a token.
- Run `cp .env.template .env` and fill with the pin numbers for your 4 buttons & LED
- Run `pip3 install requirements.txt` to install Python requirements
- Edit `/etc/rc.local` and run as your Pi user like so:
  - `su pi_user -c 'python3 /home/pi_user/snoo_buttons/main.py &'`
- Create log file location `mkdir logs`
- Reboot & it should run! (verify by running `ps aux | grep snoo` after boot and looking for 
the invocation)

## Contributing

To run tests, first run `pip3 install -r requirements_test.txt` then use `TEST=1 python3 -m pytest -W ignore::gpiozero.PinFactoryFallback -W ignore::DeprecationWarning --pdb`.
