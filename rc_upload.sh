#!/bin/bash
. $VENV/bin/activate
echo "PWD: $PWD"
ls "$PWD"
exec make DST=.
