#!/bin/bash
command=$1
xnatfolder=$2
extDir=$3
password=$4

#test
command=uploadSession
xnatfolder=BIDS-AACAZ

labels="--labels BIDS_NIFTI,BIDS_FILES,BIDS"
password="--pass $PASSWORD"
user="--user $USER"
host="--host $URL"
uploadref="--upload-by-ref False"
overwrite="--overwrite True"

session="--session AACAZXNAT_E00059"
extDir=$PWD/testtransferdir
python3 xnatTransfer.py $command $xnatfolder $extDir $host $user $password $session $project $labels $overwrite $uploadref







