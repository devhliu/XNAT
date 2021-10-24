#!/bin/bash
PROJECT="CHIDI_PRO"
USER="admin"
#PASS="#########"
read -rsp "Enter password: " PASS
URL="https://aacazxnat.arizona.edu"
OUTPUTDIR="$PWD/downloadedFiles"
RESOURCE="BIDS-AACAZ"

python downloadAllSessions.py --host $URL --user $USER --password $PASS --project $PROJECT --resource $RESOURCE --outputdir $OUTPUTDIR 
