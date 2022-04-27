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
from xnatutils.genutilsDowngrade import *
from shutil import copytree
import argparse
import json

# Constants
version = "1.1"
BIDSVERSION = "1.0.0"
BIDS_RESOURCE_FOLDER='BIDS-AACAZ'
LOG_RESOURCE_FOLDER='LOGS-AACAZ'
CONFIG_RESOURCE_FOLDER='CONFIG-AACAZ'
EDDYQC_RESOURCE_FOLDER='EDDYQC-AACAZ'
MRIQC_RESOURCE_FOLDER='MRIQC-AACAZ'

# parse arguments
parser = argparse.ArgumentParser(description="Run dcm2bids and pydeface on every file in a session")
parser.add_argument("inputDir", help="input directory")
parser.add_argument("outputDir", help="output directory")
parser.add_argument("--host", help="CNDA host", required=False)
parser.add_argument("--user", help="CNDA username", required=False)
parser.add_argument("--password", help="Password", required=False)
parser.add_argument("--cleandefaced", help="remove defaced T1w", required=False,default="N") 

args, unknown_args = parser.parse_known_args()

# if host not passed then we grab from environment
if args.host is None:
    host = os.getenv("XNAT_HOST")
else:
    host = args.host

if args.user is None:
    user = os.getenv("XNAT_USER")
else:
    user = args.user

if args.password is None:
    password = os.getenv("XNAT_PASS")
else:
    password = args.password

host = cleanServer(host)
print("XNAT host is {}".format(host))

inputDir=args.inputDir
outputDir=args.outputDir

print("Input dir: {}".format(inputDir))
print("Output dir: {}".format(outputDir))

CLEANDEFACED=isTrue(args.cleandefaced)

# obtain BIDS data
print("Copying BIDS data.")
bidsfiles=glob.glob(os.path.join(inputDir,'RESOURCES',BIDS_RESOURCE_FOLDER,'sub*'))
sub=bidsfiles[0].split('BIDS-AACAZ/')[-1]
outputfiles=os.path.join(outputDir,sub)
if os.path.exists(outputfiles):
    rmtree(outputfiles)
copytree(bidsfiles[0],outputfiles)


# delete deface anats
if CLEANDEFACED:
    T1w=glob.glob(os.path.join(outputfiles,'anat','*T1w*.*'))
    defaceanats=glob.glob(os.path.join(outputfiles,'anat','*deface.*'))
    if len(T1w) > len(defaceanats):
        for file in defaceanats:
            os.system("rm {}".format(file))

    T1w=glob.glob(os.path.join(outputfiles,'ses*','anat','*T1w*.*'))            
    defaceanats=glob.glob(os.path.join(outputfiles,'ses*','anat','*deface*.*'))
    if len(T1w) > len(defaceanats):
        for file in defaceanats:
            os.system("rm {}".format(file))


# copy datadescription
datadescription=os.path.join(inputDir,'RESOURCES',BIDS_RESOURCE_FOLDER,'dataset_description.json')
cp_command="cp {} {}".format(datadescription,outputDir)
os.system(cp_command)
print("Copied over dataset_description.json")

# Get Project name from datadescription
Project=None
try:
    with open(datadescription,'r') as datafile:
        datasetjson=json.load(datafile)
        project=datasetjson["XNATProject"]
        print("identified project as {}".format(project))
except Exception as e:
    print("Exception thrown in bidsAppCopy.py")
    print(str(e))

if not project is None:
    # Set up session
    sess = requests.Session()
    sess.verify = False
    sess.auth = (user, password)
    configfiles=os.path.join(outputDir,'derivatives')
    print("attempting to connect to host....")
    downloadProjectfiles (CONFIG_RESOURCE_FOLDER, project, configfiles, True, host,sess)
else:
    print("Project not defined. No files can be copied")


# copies freesurfer license.txt to /input/derivatives folder if it exists
LIC_LOC='https://www.dropbox.com/s/40wxja0xqw409ra/license.txt'
print("Downloading freesurfer license to output location.")
configfiles=os.path.join(outputDir,'derivatives')
if not os.access(configfiles,os.R_OK):
    os.mkdir(configfiles)

os.chdir(configfiles)
# python 3.6 uses .run?
subprocess.call(["wget",LIC_LOC])
print("Done downloading freesurfer license.")
print("Done with bids setup.")
