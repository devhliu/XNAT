#!/bin/bash
PROJECT="MYPROJECT"
USER="xnatuser"
#PASS="#########"
read -rsp "Enter password: " PASS
URL="https://xnat.org"
ROOTDIR="/path/to/root/dicom/folder"
CONFIG="$PWD/Exclusions.json"


python dicomUpload.py $URL $USER $PASS $PROJECT $ROOTDIR --config $CONFIG
