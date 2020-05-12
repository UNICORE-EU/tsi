#!/bin/sh

#
# Check status of UNICORE TSI
#
# before use, make sure that the "service name" used in 
# this file is the same as in the corresponding start.sh file

# service name
SERVICE=TSI

@cdInstall@

#
# Read basic settings
#
. @etc@/startup.properties

if [ ! -e $PID ]
then
    echo "UNICORE ${SERVICE} not running (no PID file)"
    exit 7
fi

PIDV=$(cat $PID)

if ps axww | grep -v grep | grep $PIDV | grep $SERVICE > /dev/null 2>&1 ; then
    WORKERS=$(ps --ppid $PIDV -o pid | sed "s/PID//")
    WORKERS=$(echo $WORKERS | xargs echo)
    echo "UNICORE service ${SERVICE} running with PID ${PIDV}, worker PID(s) ${WORKERS}"
    exit 0
fi

echo "warn: UNICORE service ${SERVICE} not running, but PID file $PID found"
exit 3

