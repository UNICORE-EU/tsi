#!/bin/sh

#
# Shutdown script for UNICORE TSI
#


@cdInstall@

#
# Read basic settings
#
. @etc@/startup.properties

if [ ! -e $PID ]
then
 echo "No PID file found, server probably already stopped."
 exit 0
fi

PIDVALUE=$(cat $PID)

if [ ! -e /proc/$PIDVALUE ]
then
 echo "No running TSI process found, server probably already stopped."
 rm $PID
 exit 0
fi

# find child processes (TSI workers)
WORKERS=$(ps --ppid $PIDVALUE -o pid | sed "s/PID//")

echo "Found TSI main process running with PID" $PIDVALUE
echo "Found TSI worker process(es) running with PID(s)" $WORKERS

echo $PIDVALUE $WORKERS | xargs kill -SIGKILL

echo "TSI stopped."

rm -f $PID
