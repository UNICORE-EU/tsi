#!/bin/bash

#
# Runs a single iteration of TSI processing, reading the
# message and any binary data from stdin and writing results
# and data to stdout
#
# (to start a TSI server, please use 'start.sh'!)

@cdInstall@

#
# Read basic settings
#
. @etc@/startup.properties

PARAM=$*
if [ "$PARAM" = "" ]
then
  PARAM=${CONF}/tsi.properties
fi

export PYTHONPATH=${PY}

#
# go
#
$PYTHON $PY/Runner.py $PARAM
