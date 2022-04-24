#!/bin/bash
IMVER=1.1
tar czhf xnatutils.gz ./xnatutils
docker build -t aacazxnat/bidsappcopy-setup:${IMVER} .
docker push aacazxnat/bidsappcopy-setup:${IMVER}
