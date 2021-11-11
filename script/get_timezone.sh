#!/bin/bash

# Description: Converts current timezone to seconds

ZONEDIFF=$(date +%z) # ex. +hhmm numeric time zone (e.g., -0400)
SIGN=${ZONEDIFF:0:1} # ex. +/-
HOUR=${ZONEDIFF:1:2} # ex. hh
MINUTE=${ZONEDIFF:3:2} # ex. mm

#echo $ZONEDIFF $SIGN $HOUR $MINUTE

SECHOUR=$(( 10#$HOUR * 60 * 60 ))
SECMINUTE=$(( 10#$MINUTE * 60 ))
SEC=$(( $SECHOUR + $SECMINUTE ))

#echo $SECHOUR $SECMINUTE $SEC

if [ "$SIGN" = "-" ]; then
	SEC=$(( -1 * $SEC))
fi

echo $SEC
