#!/usr/bin/env bash


BOOT_HANDLER="gnome-terminal --geometry='70x20' --title=BOOT -- bash -c '/home/delphidisplay/Desktop/CameraBasedSensor-2021/script/boot.sh'"

sleep 10
$($BOOT_HANDLER)
sleep 1
xdotool search -name BOOT windowminimize
