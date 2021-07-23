#!/bin/bash
# 
# Script: set_dt.sh
# Created: 06.05.2016
# Created By: W. Homan-Muise
# Project: E_PINOT
#
# parameters should be:   <date<,<time>,<timezone>
# example :  ./set_dt.sh 2016-06-09 14:08:00 America/Los_Angeles
#
# This is a script to sets the system time then sets the hardware clock
#
# Version: 1.0 
# Last Modified: 06.05.2016
# Last Modified By: W. Homan-Muise
#
# History:
#
# 06.05.2016 - First Version
#
# #######################################################################


# set the sudo password
adminPSWD="!ns!ght"

# get the passed parameters
newDate=$1
newTime=$2
newTZ=$3

# reset the system time zone, date and time
echo $adminPSWD | sudo -S timedatectl set-timezone $newTZ
echo $adminPSWD | sudo -S timedatectl set-time $newDate
echo $adminPSWD | sudo -S timedatectl set-time $newTime


# make the RTC set to the system settings
echo $adminPSWD | sudo -S hwclock -s
 
 
