#!/usr/bin/env bash

LOG='/home/delphidisplay/Desktop/CameraBasedSensor-2021/log/boot.log'

FUNC_NOTIFY () {
CURRTIME="$(date '+%m-%d-%Y %H:%M:%S')"
echo $CURRTIME $1 >> $LOG
echo $1

LINECOUNT=$( wc -l $LOG | awk '{ print $1 }')

if [ $LINECOUNT -ge 5500 ];
then
	echo "REMOVING OLD LOGS" >> $LOG
	sed -i '1,500d' $LOG
fi
}

FUNC_RUNOAK () {
gnome-terminal --geometry='70x20' --title=RUNOAK --working-directory=/home/delphidisplay/Desktop/CameraBasedSensor-2021 -- venv/bin/python3 runsim.py -track -full &
sleep 2
xdotool search -name RUNOAK windowminimize
}

FUNC_FLASKAPP () {
gnome-terminal --geometry='70x20' --title=FLASKAPP --working-directory=/home/delphidisplay/Desktop/CameraBasedSensor-2021 -- venv/bin/python3 app/wsgi.py &
sleep 2
xdotool search -name FLASKAPP windowminimize
}

while :
do

sleep 5

if [[ ! $(wmctrl -l) =~ "RUNOAK" ]]; then
    FUNC_NOTIFY "RUNOAK Window is Missing - Executing FUNC_RUNOAK"
    FUNC_RUNOAK
fi

if [[ ! $(wmctrl -l) =~ "FLASKAPP" ]]; then
    FUNC_NOTIFY "FLASKAPP Window is Missing - Executing FUNC_FLASKAPP"
    FUNC_FLASKAPP
fi

done
