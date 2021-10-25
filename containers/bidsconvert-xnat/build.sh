#!/bin/bash
echo "Please login to Docker as aaxazxnat"
docker  login -u "aacazxnat" docker.io

IMVERFILE=/home/chidi/repos/XNAT/VERSION
IMVER=`cat $IMVERFILE`

WORKDIR=$PWD
BUILD_DATE=$(date +%F)
DCM2BIDSVER=2.1.4

docker build -t  aacazxnat/bidsconvert-xnat:${IMVER} --build-arg BUILD_DATE=${BUILD_DATE} --build-arg VERSION=${IMVER} --build-arg DCM2BIDSVER=${DCM2BIDSVER} .

docker push  aacazxnat/bidsconvert-xnat:${IMVER}
