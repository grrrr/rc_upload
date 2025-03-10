FROM debian:bookworm-slim
RUN echo "Europe/Vienna" > /etc/timezone \
 && apt-get update --yes --quiet \
 && apt-get install --yes --quiet --no-install-recommends \
    git make python3 python3-venv pandoc curl unzip

COPY requirements.txt .
COPY Makefile .
COPY rc_upload.py .

RUN python3 -m venv .
RUN . ./bin/activate
RUN pip3 install -r requirements.txt

# for make, we need RC_SITE_ID, RC_USER, RC_PW
CMD ["make", "DST=."]
