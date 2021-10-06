#!/bin/bash
PROJECT="MYPROJECT"
USER="xnatuser"
#PASS="#########"
read -rsp "Enter password: " PASS
URL="https://xnat.org"
ROOTDIR="/path/to/main/dicom/folder"
CONFIG="Exclusions.json"
WORKDIR=$PWD/work

mkdir -p $WORKDIR

docker run -it --rm -v $WORKDIR:/work -v $ROOTDIR:/dicom -v $PWD:/input aacazxnat/dicomupload:0.1 python -m pdb /src/dicomUpload.py $URL $USER $PASS $PROJECT /dicom --config /input/$CONFIG  --workdir /work
