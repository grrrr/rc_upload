FROM python:3-slim
RUN echo "Europe/Vienna" > /etc/timezone \
 && apt-get update --yes --quiet \
 && apt-get install --yes --quiet --no-install-recommends \
    make python3 python3-venv pandoc curl unzip

ARG VENV=/opt/venv

RUN python3 -m venv $VENV

COPY requirements.txt ./

RUN . $VENV/bin/activate && pip install --no-cache-dir -r requirements.txt

COPY Makefile ./
COPY rc_upload.* ./

# for make, we need environment variables VENV, RC_SITE_ID, RC_USER, RC_PW
ENTRYPOINT ./rc_upload.sh
