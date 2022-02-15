FROM python:3.7.12-alpine3.15

RUN apk add --no-cache wget

RUN pip install \
        requests==2.23.0  \
    && \
    rm -r ${HOME}/.cache/pip

RUN apk add --update openssl
ADD bidsAppCopy.py /usr/local/bin
COPY ./xnatutils /usr/local/bin/xnatutils


LABEL org.nrg.commands="[{    \"name\": \"bidsAppCopyAACconfig\",    \"description\": \"bidsAppCopy setup command. copys files from BIDS-AACAZ and CONFIG-AACAZ\",    \"version\": \"1.1\",    \"type\": \"docker-setup\",    \"image\": \"aacazxnat/bidsappcopy-setup:1.1\",    \"command-line\": \"bidsAppCopy.py /input /output\"}]"

