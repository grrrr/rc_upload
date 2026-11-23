#!/bin/bash
. $VENV/bin/activate
exec make DST="$CI_PROJECT_DIR"
