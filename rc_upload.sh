#!/bin/bash
. $VENV/bin/activate
exec make -C "${CI_PROJECT_DIR:-$PWD}" $DST="$CI_PROJECT_DIR"
