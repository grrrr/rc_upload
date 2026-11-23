#!/bin/bash
. $VENV/bin/activate
echo -C "${CI_PROJECT_DIR:-$PWD}" $DST="$CI_PROJECT_DIR"
exec make -C "${CI_PROJECT_DIR:-$PWD}" $DST="$CI_PROJECT_DIR"
