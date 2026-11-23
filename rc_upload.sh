#!/bin/bash
. $VENV/bin/activate
echo "PATH:" $PATH ", PWD:" $PWD
exec make DST="$CI_PROJECT_DIR"
