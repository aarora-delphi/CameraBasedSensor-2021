#!/usr/bin/env bash

WINDOW_SIZE='70x20'
OAK_DIR='/home/delphidisplay/Desktop/CameraBasedSensor-2021/'
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
gnome-terminal --geometry=$WINDOW_SIZE --title=RUNOAK --working-directory=$OAK_DIR -- bash -c 'source venv/bin/activate; ./runsim.py -track -full'
xdotool search -name RUNOAK windowminimize
}

FUNC_FLASKAPP () {
gnome-terminal --geometry=$WINDOW_SIZE --title=FLASKAPP --working-directory=$OAK_DIR -- bash -c 'source venv/bin/activate; ./app.py'
xdotool search -name FLASKAPP windowminimize
}

FUNC_REDIS () {
gnome-terminal --geometry=$WINDOW_SIZE --title=REDIS --working-directory=$OAK_DIR -- bash -c 'redis-server'
xdotool search -name REDIS windowminimize
}


while :
do

sleep 5

if [[ ! $(wmctrl -l) =~ "RUNOAK" ]]; then
    FUNC_NOTIFY "RUNOAK Window is Missing - Executing FUNC_RUNOAK"
    FUNC_RUNOAK
    sleep 5
fi

if [[ ! $(wmctrl -l) =~ "FLASKAPP" ]]; then
    FUNC_NOTIFY "FLASKAPP Window is Missing - Executing FUNC_FLASKAPP"
    FUNC_FLASKAPP
    sleep 5
fi

if [[ ! $(wmctrl -l) =~ "REDIS" ]]; then
    FUNC_NOTIFY "REDIS Window is Missing - Executing FUNC_REDIS"
    FUNC_REDIS
    sleep 5
fi

done
