#!/bin/bash
. $VENV/bin/activate
echo "PWD: $PWD"
ls "$PWD/cache"
exec make DST=.
