#!/bin/bash
PROJECT="MYTESTPROJECT"
USER="user"
#PASS="#########"
read -rsp "Enter password: " PASS
URL="https://myxnat.edu"
ROOTDIR="/tmp/testupload"
CONFIG="Exclusions.json"
WORKDIR=$PWD/work

mkdir -p $WORKDIR

docker run -it --rm -v $WORKDIR:/work -v $ROOTDIR:/dicom -v $PWD:/input aacazxnat/dicomupload:0.1 python /src/dicomUpload.py $URL $USER $PASS $PROJECT /dicom --config /input/$CONFIG  --workdir /work
