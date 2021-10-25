#!/bin/bash
PROJECT="MYPROJECT"
USER="myuserid"
#PASS="#########"
read -rsp "Enter password: " PASS
URL="https:/xnat.org"
ROOTDIR="$PWD/testupload"
CONFIG="$PWD/Exclusions.json"


python dicomUpload.py $URL $USER $PASS $PROJECT $ROOTDIR --config $CONFIG
