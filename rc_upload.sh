#!/bin/bash
. $VENV/bin/activate
echo CI_PROJECT_DIR: "$CI_PROJECT_DIR"
exec make DST=$CI_PROJECT_DIR
