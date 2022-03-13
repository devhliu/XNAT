#!/bin/bash
IMVER=0.1
tar czhf xnatutils.gz ./xnatutils
docker build -t aacazxnat/qcproject-xnat:${IMVER} .
docker push  aacazxnat/qcproject-xnat:${IMVER}
