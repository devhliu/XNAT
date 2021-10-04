FROM python:2.7.14-alpine3.6

RUN apk add --no-cache wget

RUN pip install \
        docopt \
    && \
    rm -r ${HOME}/.cache/pip

RUN apk add --update openssl
ADD bidsAppCopy.py /usr/local/bin
LABEL org.nrg.commands="[{\"name\": \"bidsAppCopyAAC\", \"command-line\": \"bidsAppCopy.py /input /output\", \"image\": \"aacazxnat/bidsappcopy-setup:1.0\", \"version\": \"1.0\", \"type\": \"docker-setup\", \"description\": \"bidsAppCopy setup command copies files from BIDS-AACAZ for bids app compatibility.\"}]"
