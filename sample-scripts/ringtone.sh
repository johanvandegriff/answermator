#!/bin/bash
if [[ "$1" == "register" ]]; then
    echo 88:ringtone
elif [[ "$1" == "run" ]]; then
    echo "shell script activated, args: $@"
    echo "playing the ringtone"
    paplay ~/phonebot/answermator-app/ringtones/marimba.ogg
fi
