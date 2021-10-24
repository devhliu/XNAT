#!/bin/bash
command=$1
xnatfolder=$2
extDir=$3
password=$4

#test
command=uploadSession
xnatfolder=PHYSIO-ORBISYS

labels="--labels PHYSIO_SIEMENS,PHYSIO_FILES,PHYSIO"
password="--pass $PASSWORD"
user="--user $USER"
host="--host $URL"
uploadref="--upload-by-ref False"
overwrite="--overwrite True"

#extDir=/home/chidi/projects/CHEN-STN/bidsphysio/sessionC_20190814_physiologicalSignals/preC
#session="--session AACAZXNAT_E00026"
#python3 -m pdb xnatTransfer.py $command $xnatfolder $extDir $host $user $password $session $project $labels $overwrite $uploadref


session="--session AACAZXNAT_E00030"
extDir=/home/chidi/projects/CHEN-STN/bidsphysio/sessionC_20190814_physiologicalSignals/postC
python3 xnatTransfer.py $command $xnatfolder $extDir $host $user $password $session $project $labels $overwrite $uploadref

session="--session AACAZXNAT_E00050"
extDir=/home/chidi/projects/CHEN-STN/bidsphysio/sessionD_20190904_physiologicalSignals/preD
python3 xnatTransfer.py $command $xnatfolder $extDir $host $user $password $session $project $labels $overwrite $uploadref

session="--session AACAZXNAT_E00052"
extDir=/home/chidi/projects/CHEN-STN/bidsphysio/sessionD_20190904_physiologicalSignals/postD
python3 xnatTransfer.py $command $xnatfolder $extDir $host $user $password $session $project $labels $overwrite $uploadref

session="--session AACAZXNAT_E00051"
extDir=/home/chidi/projects/CHEN-STN/bidsphysio/sessionE_20190925_physiologicalSignals/preE
python3 xnatTransfer.py $command $xnatfolder $extDir $host $user $password $session $project $labels $overwrite $uploadref

session="--session AACAZXNAT_E00054"
extDir=/home/chidi/projects/CHEN-STN/bidsphysio/sessionE_20190925_physiologicalSignals/postE
python3 xnatTransfer.py $command $xnatfolder $extDir $host $user $password $session $project $labels $overwrite $uploadref

