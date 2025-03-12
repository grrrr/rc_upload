#!/bin/bash
. $VENV/bin/activate
echo "PWD: $PWD"
find / -name references.bib
exec make DST=.
