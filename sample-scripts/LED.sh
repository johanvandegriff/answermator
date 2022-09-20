#!/bin/bash
if [[ "$1" == "register" ]]; then
    # https://raspberrypi-aa.github.io/session2/bash.html
    #   Exports pin to userspace
    sudo echo "21" > /sys/class/gpio/export > /dev/null 2> /dev/null
    # Sets pin 21 as an output
    echo "out" | sudo tee /sys/class/gpio/gpio21/direction > /dev/null 2> /dev/null
    echo "9999:LED on (pin 21),9998:LED off (pin 21)"
elif [[ "$1" == "run" ]]; then
    echo "shell script activated, args: $@"
    if [[ "$3" == "True" ]]; then
        if [[ "$2" == 9999 ]]; then
            # Sets pin 21 to high
            echo "1" > /sys/class/gpio/gpio21/value
            echo "(shell script) turn LED on"
        else
            # Sets pin 21 to low
            echo "0" > /sys/class/gpio/gpio21/value
            echo "(shell script) turn LED off"
        fi
    else
        echo "(shell script) not logged in"
    fi
fi
