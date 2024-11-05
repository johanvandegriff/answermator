# Answermator

[about page](https://jjv.sh/answermator/)

## SD Card Image Install
 * Download the zipped image from the [releases page](https://github.com/johanvandegriff/answermator/releases)
 * Extract it and write it to an SD card at least 8GB. You can install [balena etcher](https://www.balena.io/etcher/) to do both of these in 1 step.

## Manual Install (work in progress)
 * install the [Raspberry Pi OS](https://www.raspberrypi.com/software/) to an SD card
 * log in to the pi zero and run these commands:
```bash
cd
mkdir phonebot
cd phonebot
git clone https://github.com/johanvandegriff/answermator
#TODO there are more commands needed to give permission to access the pins and install the right python libraries
crontab -e #and add the following:
```
```
@reboot /home/pi/phonebot/answermator-app/launch.sh
```
 * reboot the pi with the `reboot` command
