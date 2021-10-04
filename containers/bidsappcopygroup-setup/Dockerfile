FROM python:2.7.14-alpine3.6

RUN pip install \
        docopt \
    && \
    rm -r ${HOME}/.cache/pip

RUN   apk update \                                                                                                                                                                                                                        
  &&   apk add ca-certificates wget \                                                                                                                                                                                                      
  &&   update-ca-certificates  


ADD bidsAppCopyGroup.py /usr/local/bin
LABEL org.nrg.commands="[{\"name\": \"bidsAppCopyGroupAAC\", \"command-line\": \"bidsAppCopyGroup.py /input /output\", \"image\": \"aacazxnat/bidsappcopygroup-setup:1.0\", \"version\": \"1.0\", \"type\": \"docker-setup\", \"description\": \"bidsAppCopyGroup setup command -copies files from BIDS-AAZ for bids app compatibility.\"}]"
