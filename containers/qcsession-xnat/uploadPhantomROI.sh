#!/bin/bash

# test session upload
command=uploadProject
xnatfolder=PHANTOMROI-AACAZ

labels="--labels PHANTOM_ROI,PHANTOM_ROI_FILES,ROI"
host="--host https://aacazxnat.arizona.edu"
overwrite="--overwrite True"

project="--project U19_PILOT"
extDir="/mnt/PhantomROI"
DEBUG="-m pdb"
DEBUG=""

docker run --rm -it -v $PWD:/mnt aacazxnat/xnatupload:0.1 python $DEBUG /src/xnatUpload.py $command $xnatfolder $extDir $host $project $labels $overwrite $uploadref

