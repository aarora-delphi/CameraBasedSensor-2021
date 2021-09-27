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
gnome-terminal --geometry=$WINDOW_SIZE --title=RUNOAK --working-directory=$OAK_DIR -- bash -c './runoak.py -track'
xdotool search -name RUNOAK windowminimize
}

# FUNC_SYNCTRACK () {
# gnome-terminal --geometry=$WINDOW_SIZE --title=SYNCTRACK --working-directory=$OAK_DIR -- bash -c './synctrack.py'
# xdotool search -name SYNCTRACK windowminimize
# }

while :
do

if [[ ! $(wmctrl -l) =~ "RUNOAK" ]]; then
    FUNC_NOTIFY "RUNOAK Window is Missing - Executing RUNOAK"
    FUNC_RUNOAK
fi

sleep 5

# if [[ ! $(wmctrl -l) =~ "SYNCTRACK" ]]; then
#     FUNC_NOTIFY "SYNCTRACK Window is Missing - Executing SYNCTRACK"
#     FUNC_SYNCTRACK
# fi

# sleep 5

done
