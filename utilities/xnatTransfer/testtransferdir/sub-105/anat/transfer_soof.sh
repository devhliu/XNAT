#!/bin/bash
command=$1
xnatfolder=$2
extDir=$3
password=$4

#test
command=uploadSession
xnatfolder=FMRIPREP-ORBISYS

labels="--labels FMRIPREP_NIFTI,FMRIPREP_FILES,FMRIPREP"
password="--pass NKlab2019"
user="--user admin"
host="--host https://aacazxnat.arizona.edu"
uploadref="--upload-by-ref False"
overwrite="--overwrite True"

session="--session AACAZXNAT_E00049"

extDir=/data/xnat/build/a5e2cfd7-7481-401e-bd09-c3678370afed/BIDS/sub-1006/FMRIPREP

python3 -m pdb xnatTransfer.py $command $xnatfolder $extDir $host $user $password $session $project $labels $overwrite $uploadref

