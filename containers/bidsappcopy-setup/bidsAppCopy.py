#!/usr/bin/env python

"""bidsAppCopy
Copy files from BIDS-ORBISYS folder as output for Bids Apps

Usage:
    bidsAppCopy.py <inputDir> <outputDir>
    bidsAppCopy.py (-h | --help)
    bidsAppCopy.py --version

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

bidsfiles=glob(os.path.join(inputDir,'RESOURCES','BIDS-AACAZ','sub*'))
sub=bidsfiles[0].split('BIDS-AACAZ/')[-1]
outputfiles=os.path.join(outputDir,sub)

if os.path.exists(outputfiles):
    shutil.rmtree(outputfiles)

shutil.copytree(bidsfiles[0],outputfiles)

print("Done copying BIDS data.")

print("Constructing dummy BIDS dataset description for compatibility with BIDS app.")
dataset_description=OrderedDict()
dataset_description['Name']='Dummy Project'
dataset_description['BIDSVersion']=BIDSVERSION
dataset_description['License']=""
dataset_description['ReferencesAndLinks']=""
with open(os.path.join(outputDir,'dataset_description.json'),'w') as datasetjson:
     json.dump(dataset_description,datasetjson)
print("Done creating dummy BIDS data description.")

# copies freesurfer license.txt to output folder if it exists
LIC_LOC='https://www.dropbox.com/s/40wxja0xqw409ra/license.txt'
print("Downloading freesurfer license to output location.")
os.chdir(outputDir)

# python 3.6 uses .run?
subprocess.call(["wget",LIC_LOC])
print("Done downloading freesurfer license.")
print("Done with bids setup.")
