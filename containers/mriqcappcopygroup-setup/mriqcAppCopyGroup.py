#!/usr/bin/env python

"""mriqcAppCopyGroup
Copy files from all BIDS-AAZ and MRIQC-AAZ folders for a project output for Bids MRIQC App

Usage:
    mriqcAppCopyGroup.py <inputDir> <outputDir>
    mriqcAppCopyGroup.py (-h | --help)
    mriqcAppCopyGroup.py --version

Options:
    -h --help           Show the usage
    --version           Show the version
    <inputDir>          Directory with BIDS files.
                        This is a BIDS-ORBISYS Resource file
    <outputDir>         Directory in which BIDS formatted files should be written.
"""

import os
import sys
import json
import csv
import shutil
from glob import glob
from docopt import docopt
import datetime
from collections import OrderedDict
import subprocess

version = "1.0"
BIDSVERSION = "1.0.0"
args = docopt(__doc__, version=version)

inputDir = args['<inputDir>']
outputDir = args['<outputDir>']

print("Input dir: {}".format(inputDir))
print("Output dir: {}".format(outputDir))

print("Copying BIDS data.")

participants=[]
override=True
bidsession=glob(os.path.join(inputDir,'*','RESOURCES','BIDS-AACAZ','sub*','*'))
for sessSingle in bidsession:
    bidsubj=sessSingle.split('/')[-2]
    participants.append(bidsubj)

    bidsesh=sessSingle.split('/')[-1]
    subjdir=os.path.join(outputDir,bidsubj)
    seshdir=os.path.join(outputDir,bidsubj, bidsesh)
    if os.path.isdir(subjdir):
        print(subjdir + ' already exists')
        if os.path.isdir(seshdir):
            if override:
               print(seshdir + ' exists - deleting')
               shutil.rmtree(seshdir)
            else:
               TIMESTAMP=datetime.datetime.now().strftime("%m%d%y%H%M%S%p")
               oldseshdir=seshdir
               seshdir=seshdir + '_' + TIMESTAMP
               print('files will be copied to ' + seshdir + 'instead of ' + oldseshdir + ' - override set to FALSE')
    else:
         print('Creating '+subjdir)
         os.mkdir(subjdir)

    print('Copying from ' + sessSingle + ' to ' + seshdir)
    shutil.copytree(sessSingle,seshdir)

print("Constructing BIDS dataset description")
dataset_description=OrderedDict()
dataset_description['Name'] =inputDir.split('/')[-2]
dataset_description['BIDSVersion']=BIDSVERSION
dataset_description['License']=""
dataset_description['ReferencesAndLinks']=""
with open(os.path.join(outputDir,'dataset_description.json'),'w') as datasetjson:
     json.dump(dataset_description,datasetjson)

partSet=set(participants)
participants=list(partSet)
print("Constructing participants tsv file")
with open(os.path.join(outputDir,'participants.tsv'),'w') as subjtsv:
      csv_writer = csv.writer(subjtsv,delimiter=',')
      for participant in participants:
          csv_writer.writerow([participant])

# copies freesurfer license.txt to output folder if it exists
# This is not really necessary as highly unlikely to run FMRIPREP this way.
# This is a bit of a hack as is not platform agnostic  - using wget
LIC_LOC='https://www.dropbox.com/s/40wxja0xqw409ra/license.txt'
print("Downloading freesurfer license to output location") 
os.chdir(outputDir)

# python 3.6 uses .run?
subprocess.call(["wget",LIC_LOC])

print("Done.")
