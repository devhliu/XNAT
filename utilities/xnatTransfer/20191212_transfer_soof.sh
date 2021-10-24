#!/bin/bash
command=$1
xnatfolder=$2
extDir=$3
password=$4

#test
command=uploadSession
xnatfolder=FMRIPREP-ORBISYS_test

labels="--labels FMRIPREP_NIFTI,FMRIPREP_FILES,FMRIPREP"
password="--pass $PASSWORD"
user="--user $USER"
host="--host $URL"
uploadref="--upload-by-ref False"
overwrite="--overwrite True"

session="--session AACAZXNAT_E00065"
extDir=/data/xnat/build/5a77b398-72f8-4362-b99e-ceb915f8a99e/BIDS/sub-1030/FMRIPREP
python3 -m pdb  xnatTransfer.py $command $xnatfolder $extDir $host $user $password $session $project $labels $overwrite $uploadref

#session="--session AACAZXNAT_E00070"
#extDir=/data/xnat/build/109a59ef-c9c7-427f-8774-e13beb7c608d/BIDS/sub-1031/FMRIPREP
#python3  xnatTransfer.py $command $xnatfolder $extDir $host $user $password $session $project $labels $overwrite $uploadref

#session="--session AACAZXNAT_E00076" 
#extDir=/data/xnat/build/c9d399cc-573d-412a-8f23-1efb6a845b4e/BIDS/sub-1033/FMRIPREP 
#python3 xnatTransfer.py $command $xnatfolder $extDir $host $user $password $session $project $labels $overwrite $uploadref

#session="--session AACAZXNAT_E00078" 
#extDir=/data/xnat/build/21ed75d5-374c-482e-b2d5-f6beea494b89/BIDS/sub-1034/FMRIPREP 
#python3 xnatTransfer.py $command $xnatfolder $extDir $host $user $password $session $project $labels $overwrite $uploadref






