FROM python:3-slim
RUN echo "Europe/Vienna" > /etc/timezone \
 && apt-get update --yes --quiet \
 && apt-get install --yes --quiet --no-install-recommends \
    make python3 python3-venv pandoc curl unzip

ENV VENV=/opt/venv

RUN python3 -m venv $VENV

COPY requirements.txt ./

RUN source $VENV/bin/activate && pip install --no-cache-dir -r requirements.txt

COPY Makefile ./
COPY rc_upload.py ./

# for make, we need RC_SITE_ID, RC_USER, RC_PW
CMD source $VENV/bin/activate && exec make DST=.
