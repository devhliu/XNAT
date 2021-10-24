#!/bin/bash
USER="admin"
#PASS="#########"
read -rsp "Enter password: " PASS
URL="https://aacazxnat.arizona.edu"
OUTPUTDIR="$PWD/downloadedFiles"
RESOURCE="BIDS-AACAZ"
SESSION="AACAZXNAT_E00048"

python downloadSession.py --host $URL --user $USER --password $PASS --session $SESSION --resource $RESOURCE --outputdir $OUTPUTDIR 
