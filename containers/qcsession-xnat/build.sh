#!/bin/bash
IMVER=0.1
tar czhf xnatutils.gz ./xnatutils
docker build -t aacazxnat/qcsession-xnat:${IMVER} .
docker push  aacazxnat/qcsession-xnat:${IMVER}
