#!/bin/bash
command=$1
xnatfolder=$2
extDir=$3
password=$4

#test
command=uploadSession
xnatfolder=FMRIPREP-ORBISYS

labels="--labels FMRIPREP_NIFTI,FMRIPREP_FILES,FMRIPREP"
password="--pass $PASSWORD"
user="--user $USER"
host="--host $URL"
uploadref="--upload-by-ref False"
overwrite="--overwrite True"

session="--session AACAZXNAT_E00121"
extDir=/data/xnat/build/94ba72f3-05c0-44f9-965b-9959c5f68861/BIDS/sub-1042/FMRIPREP
python3 xnatTransfer.py $command $xnatfolder $extDir $host $user $password $session $project $labels $overwrite $uploadref







