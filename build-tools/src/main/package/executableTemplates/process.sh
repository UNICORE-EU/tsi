#!/bin/bash

#
# Runs a single iteration of TSI processing, reading the
# message and any binary data from stdin and writing results
# and binary data (base64-encoded) to stdout
#
# (to start a TSI server, please use 'start.sh'!)

PYTHON="python3"
export PYTHONPATH=@lib@

$PYTHON @lib@/Runner.py
