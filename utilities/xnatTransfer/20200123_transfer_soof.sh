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

session="--session AACAZXNAT_E00108"
extDir=/data/xnat/build/4d925b8c-299c-4241-8faa-97de7ca8b54f/BIDS/sub-1012/FMRIPREP
python3 xnatTransfer.py $command $xnatfolder $extDir $host $user $password $session $project $labels $overwrite $uploadref







