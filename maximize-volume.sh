#!/bin/sh

pactl set-sink-mute "alsa_output.pci-0000_00_1b.0.analog-stereo" 0
pactl set-sink-volume "alsa_output.pci-0000_00_1b.0.analog-stereo" 0x10000
