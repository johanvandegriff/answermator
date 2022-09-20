#!/bin/bash
#https://stackoverflow.com/questions/42497130/audio-doesnt-play-with-crontab-on-raspberry-pi#43436895
#https://wiki.archlinux.org/title/PulseAudio#Play_sound_from_a_non-interactive_shell_.28systemd_service.2C_cron.29
# export XDG_RUNTIME_DIR=/run/user/1000
test -f ~/answermator.log && cp ~/answermator.log ~/answermator.log.last
authbind --deep python2 `dirname $0`/interface.py $@ 2>&1 | tee /home/pi/answermator.log
