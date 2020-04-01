import argparse
import collections
import json
import requests
import os
import glob
import sys
import subprocess
import time
import zipfile
import tempfile
import dicom as dicomLib
from shutil import copy as fileCopy
from shutil import rmtree
from nipype.interfaces.dcm2nii import Dcm2nii
from collections import OrderedDict
import requests.packages.urllib3
requests.packages.urllib3.disable_warnings()


def cleanServer(server):
    server.strip()
    if server[-1] == '/':
        server = server[:-1]
    if server.find('http') == -1:
        server = 'https://' + server
    return server


def isTrue(arg):
    return arg is not None and (arg == 'Y' or arg == '1' or arg == 'True')


def download(name, pathDict):
    if os.access(pathDict['absolutePath'], os.R_OK):
        try:
            os.symlink(pathDict['absolutePath'], name)
        except:
            fileCopy(pathDict['absolutePath'], name)
            print 'Copied %s.' % pathDict['absolutePath']
    else:
        with open(name, 'wb') as f:
            r = get(pathDict['URI'], stream=True)

            for block in r.iter_content(1024):
                if not block:
                    break

                f.write(block)
        print 'Downloaded file %s.' % name

def zipdir(dirPath=None, zipFilePath=None, includeDirInZip=True):
    if not zipFilePath:
        zipFilePath = dirPath + ".zip"
    if not os.path.isdir(dirPath):
        raise OSError("dirPath argument must point to a directory. "
            "'%s' does not." % dirPath)
    parentDir, dirToZip = os.path.split(dirPath)
    def trimPath(path):
        archivePath = path.replace(parentDir, "", 1)
        if parentDir:
            archivePath = archivePath.replace(os.path.sep, "", 1)
        if not includeDirInZip:
            archivePath = archivePath.replace(dirToZip + os.path.sep, "", 1)
        return os.path.normcase(archivePath)
    outFile = zipfile.ZipFile(zipFilePath, "w",
        compression=zipfile.ZIP_DEFLATED)
    for (archiveDirPath, dirNames, fileNames) in os.walk(dirPath):
        for fileName in fileNames:
            filePath = os.path.join(archiveDirPath, fileName)
            outFile.write(filePath, trimPath(filePath))
        # Make sure we get empty directories as well
        if not fileNames and not dirNames:
            zipInfo = zipfile.ZipInfo(trimPath(archiveDirPath) + "/")
            # some web sites suggest doing
            # zipInfo.external_attr = 16
            # or
            # zipInfo.external_attr = 48
            # Here to allow for inserting an empty directory.  Still TBD/TODO.
            outFile.writestr(zipInfo, "")
    outFile.close()

BIDSVERSION = "1.0.1"

parser = argparse.ArgumentParser(description="Use cbedetti/dcm2bids to convert dicoms to bids format")
parser.add_argument("--host", default="https://xnat.org", help="XNAT host", required=True)
parser.add_argument("--user", help="CNDA username", required=True)
parser.add_argument("--password", help="Password", required=True)
parser.add_argument("--session", help="Session ID", required=True)
parser.add_argument("--subject", help="Subject Label", required=False)
parser.add_argument("--session_label", help="session Label",  nargs='?', required=False)
parser.add_argument("--project", help="Project", required=False)
parser.add_argument("--dicomdir", help="Root output directory for DICOM files", required=True)
parser.add_argument("--niftidir", help="Root output directory for NIFTI files", required=True)
parser.add_argument("--overwrite", help="Overwrite NIFTI files if they exist")
parser.add_argument("--upload-by-ref", help="Upload \"by reference\". Only use if your host can read your file system.")
parser.add_argument("--workflowId", help="Pipeline workflow ID")
parser.add_argument('--version', action='version', version='%(prog)s 1')

args, unknown_args = parser.parse_known_args()
host = cleanServer(args.host)
session = args.session
session_label = args.session_label
subject = args.subject
project = args.project
overwrite = isTrue(args.overwrite)
dicomdir = args.dicomdir
niftidir = args.niftidir
workflowId = args.workflowId
uploadByRef = isTrue(args.upload_by_ref)
dcm2niixArgs = unknown_args if unknown_args is not None else []

bidsdir = niftidir + "/BIDS"

builddir = os.getcwd()

# Set up working directory
if not os.access(dicomdir, os.R_OK):
    print 'Making DICOM directory %s' % dicomdir
    os.mkdir(dicomdir)
if not os.access(niftidir, os.R_OK):
    print 'Making NIFTI directory %s' % niftidir
    os.mkdir(niftidir)
if not os.access(bidsdir, os.R_OK):
    print 'Making NIFTI BIDS directory %s' % bidsdir
    os.mkdir(bidsdir)

# Set up session
sess = requests.Session()
sess.verify = False
sess.auth = (args.user, args.password)


def get(url, **kwargs):
    try:
        r = sess.get(url, **kwargs)
        r.raise_for_status()
    except (requests.ConnectionError, requests.exceptions.RequestException) as e:
        print "Request Failed"
        print "    " + str(e)
        sys.exit(1)
    return r

if project is None or subject is None:
    # Get project ID and subject ID from session JSON
    print "Get project and subject ID for session ID %s." % session
    r = get(host + "/data/experiments/%s" % session, params={"format": "json", "handler": "values", "columns": "project,subject_ID"})
    sessionValuesJson = r.json()["ResultSet"]["Result"][0]
    project = sessionValuesJson["project"] if project is None else project
    subjectID = sessionValuesJson["subject_ID"]
    print "Project: " + project
    print "Subject ID: " + subjectID

    if subject is None:
        print
        print "Get subject label for subject ID %s." % subjectID
        r = get(host + "/data/subjects/%s" % subjectID, params={"format": "json", "handler": "values", "columns": "label"})
        subject = r.json()["ResultSet"]["Result"][0]["label"]
        print "Subject label: " + subject

session_label_all = session_label
if session_label is None:
	# get session label
	r = get(host + "/data/experiments/%s" % session, params={"format": "json", "handler": "values", "columns": "label"})
	sessionValuesJson = r.json()["ResultSet"]["Result"][0]
	session_label_all = sessionValuesJson["label"]
	session_label = session_label_all.split('_')[0]

	
subdicomdir = os.path.join(dicomdir, subject)
if not os.path.isdir(subdicomdir):
    print 'creating DICOM/subject directory %s.' % subdicomdir
    os.mkdir(subdicomdir)
		
#make dicom dir unique - might not be truly necessary
sesdicomdir = os.path.join(subdicomdir, session_label_all)
if not os.path.isdir(sesdicomdir):
    print 'creating DICOM/subject/session directory %s.' % sesdicomdir
    os.mkdir(sesdicomdir)
	
# Get list of scan ids
print
print "Get scan list for session ID %s." % session
r = get(host + "/data/experiments/%s/scans" % session, params={"format": "json"})
scanRequestResultList = r.json()["ResultSet"]["Result"]
scanIDList = [scan['ID'] for scan in scanRequestResultList]
seriesDescList = [scan['series_description'] for scan in scanRequestResultList]  # { id: sd for (scan['ID'], scan['series_description']) in scanRequestResultList }
print 'Found scans %s.' % ', '.join(scanIDList)
print 'Series descriptions %s' % ', '.join(seriesDescList)

# Fall back on scan type if series description field is empty
if set(seriesDescList) == set(['']):
    seriesDescList = [scan['type'] for scan in scanRequestResultList]
    print 'Fell back to scan types %s' % ', '.join(seriesDescList)

## Get site- and project-level configs
#bidsmaplist = []

print "Get project BIDS dcm2bids map"
r = sess.get(host + "/data/projects/%s/config/dcm2bids/bidsconfig" % project, params={"contents": True})
if r.ok:
    config = r.json()
    dcm2bids_config=os.path.join(bidsdir,'dcm2bids_config.json')
    with open(dcm2bids_config, 'w') as outfile:
        json.dump(config, outfile)
else:
    print "Could not read project BIDS map"


# Cheat and reverse scanid and seriesdesc lists so numbering is in the right order
for scanid, seriesdesc in zip(reversed(scanIDList), reversed(seriesDescList)):
    print
    print 'Beginning process for scan %s.' % scanid
    os.chdir(builddir)

    # Get scan resources
    print "Get scan resources for scan %s." % scanid
    r = get(host + "/data/experiments/%s/scans/%s/resources" % (session, scanid), params={"format": "json"})
    scanResources = r.json()["ResultSet"]["Result"]
    print 'Found resources %s.' % ', '.join(res["label"] for res in scanResources)

    ##########
    # Do initial checks to determine if scan should be skipped
    hasNifti = any([res["label"] == "NIFTI" for res in scanResources])  # Store this for later
    if hasNifti and not overwrite:
        print "Scan %s has a preexisting NIFTI resource, and I am running with overwrite=False. Skipping." % scanid
        continue

    dicomResourceList = [res for res in scanResources if res["label"] == "DICOM"]
    imaResourceList = [res for res in scanResources if res["format"] == "IMA"]

    if len(dicomResourceList) == 0 and len(imaResourceList) == 0:
        print "Scan %s has no DICOM or IMA resource." % scanid
        # scanInfo['hasDicom'] = False
        continue
    elif len(dicomResourceList) == 0 and len(imaResourceList) > 1:
        print "Scan %s has more than one IMA resource and no DICOM resource. Skipping." % scanid
        # scanInfo['hasDicom'] = False
        continue
    elif len(dicomResourceList) > 1 and len(imaResourceList) == 0:
        print "Scan %s has more than one DICOM resource and no IMA resource. Skipping." % scanid
        # scanInfo['hasDicom'] = False
        continue
    elif len(dicomResourceList) > 1 and len(imaResourceList) > 1:
        print "Scan %s has more than one DICOM resource and more than one IMA resource. Skipping." % scanid
        # scanInfo['hasDicom'] = False
        continue

    dicomResource = dicomResourceList[0] if len(dicomResourceList) > 0 else None
    imaResource = imaResourceList[0] if len(imaResourceList) > 0 else None

    usingDicom = True if (len(dicomResourceList) == 1) else False

    if dicomResource is not None and dicomResource["file_count"]:
        if int(dicomResource["file_count"]) == 0:
            print "DICOM resource for scan %s has no files. Checking IMA resource." % scanid
            if imaResource["file_count"]:
                if int(imaResource["file_count"]) == 0:
                    print "IMA resource for scan %s has no files either. Skipping." % scanid
                    continue
            else:
                print "IMA resource for scan %s has a blank \"file_count\", so I cannot check it to see if there are no files. I am not skipping the scan, but this may lead to errors later if there are no files." % scanid
    elif imaResource is not None and imaResource["file_count"]:
        if int(imaResource["file_count"]) == 0:
            print "IMA resource for scan %s has no files. Skipping." % scanid
            continue
    else:
        print "DICOM and IMA resources for scan %s both have a blank \"file_count\", so I cannot check to see if there are no files. I am not skipping the scan, but this may lead to errors later if there are no files." % scanid

    ##########
    # Prepare DICOM directory structure
    print
    scanDicomDir = os.path.join(sesdicomdir, scanid)
    if not os.path.isdir(scanDicomDir):
        print 'Making scan DICOM directory %s.' % scanDicomDir
        os.mkdir(scanDicomDir)
    # Remove any existing files in the builddir.
    # This is unlikely to happen in any environment other than testing.
    for f in os.listdir(scanDicomDir):
        os.remove(os.path.join(scanDicomDir, f))

    ##########
    # Get list of DICOMs/IMAs

    # set resourceid. This will only be set if hasIma is true and we've found a resource id
    resourceid = None

    if not usingDicom:

        print 'Get IMA resource id for scan %s.' % scanid
        r = get(host + "/data/experiments/%s/scans/%s/resources" % (session, scanid), params={"format": "json"})
        resourceDict = {resource['format']: resource['xnat_abstractresource_id'] for resource in r.json()["ResultSet"]["Result"]}

        if resourceDict["IMA"]:
            resourceid = resourceDict["IMA"]
        else:
            print "Couldn't get xnat_abstractresource_id for IMA file list."

    # Deal with DICOMs
    print 'Get list of DICOM files for scan %s.' % scanid

    if usingDicom:
        filesURL = host + "/data/experiments/%s/scans/%s/resources/DICOM/files" % (session, scanid)
    elif resourceid is not None:
        filesURL = host + "/data/experiments/%s/scans/%s/resources/%s/files" % (session, scanid, resourceid)
    else:
        print "Trying to convert IMA files but there is no resource id available. Skipping."
        continue

    r = get(filesURL, params={"format": "json"})
    # I don't like the results being in a list, so I will build a dict keyed off file name
    dicomFileDict = {dicom['Name']: {'URI': host + dicom['URI']} for dicom in r.json()["ResultSet"]["Result"]}

    # Have to manually add absolutePath with a separate request
    r = get(filesURL, params={"format": "json", "locator": "absolutePath"})
    for dicom in r.json()["ResultSet"]["Result"]:
        dicomFileDict[dicom['Name']]['absolutePath'] = dicom['absolutePath']

    ##########
    # Download DICOMs
    print "Downloading files for scan %s." % scanid
    os.chdir(scanDicomDir)

    # Check secondary
    # Download any one DICOM from the series and check its headers
    # If the headers indicate it is a secondary capture, we will skip this series.
    dicomFileList = dicomFileDict.items()

    (name, pathDict) = dicomFileList[0]
    download(name, pathDict)

    if usingDicom:
        print 'Checking modality in DICOM headers of file %s.' % name
        d = dicomLib.read_file(name)
        modalityHeader = d.get((0x0008, 0x0060), None)
        if modalityHeader:
            print 'Modality header: %s' % modalityHeader
            modality = modalityHeader.value.strip("'").strip('"')
            if modality == 'SC' or modality == 'SR':
                print 'Scan %s is a secondary capture. Skipping.' % scanid
                continue
        else:
            print 'Could not read modality from DICOM headers. Skipping.'
            continue

    ##########
    # Download remaining DICOMs
    for name, pathDict in dicomFileList[1:]:
        download(name, pathDict)

    os.chdir(builddir)
    print 'Done downloading for scan %s.' % scanid
    print


subjectBidsDir=os.path.join(bidsdir,"sub-"+subject)
if not os.path.isdir(subjectBidsDir):
    print 'creating BIDS/subject directory %s.' % subjectBidsDir
    os.mkdir(subjectBidsDir)
        
sessionBidsDir=os.path.join(subjectBidsDir,"ses-"+session_label)
if not os.path.isdir(sessionBidsDir):
    print 'creating BIDS/subject/session directory %s.' % sessionBidsDir
    os.mkdir(sessionBidsDir)

if overwrite:
    dcm2bids_command = "dcm2bids -d {} -p {} -s {} -c {} -o {} --clobber".format(sesdicomdir, subject, session_label, dcm2bids_config, sessionBidsDir ).split()
else:    
    dcm2bids_command = "dcm2bids -d {} -p {} -s {} -c {} -o {}".format(sesdicomdir, subject, session_label, dcm2bids_config, sessionBidsDir ).split()
print "Executing command: " + " ".join(dcm2bids_command)
print subprocess.check_output(dcm2bids_command)
	

#delete temporary folder
tmpBidsDir=os.path.join(sessionBidsDir,'tmp_dcm2bids')
print 'Cleaning up %s directory.' % tmpBidsDir
rmtree(tmpBidsDir)

	
##########
# Upload results
print
print 'Preparing to upload files for session %s.' % session

#test without deleting

#Make this more flexible
#hasBidsDir = True
# If we have a NIFTI resource and we've reached this point, we know overwrite=True.
# We should delete the existing NIFTI resource.
#if hasBidsDir:
#    print "Session %s has a preexisting BIDSDIR resource. Deleting it now." % session

#    try:
#        queryArgs = {}
#        if workflowId is not None:
#            queryArgs["event_id"] = workflowId
#        r = sess.delete(host + "/data/experiments/%s/resources/BIDS-ORBISYS" % (session), params=queryArgs)
#        r.raise_for_status()
#    except (requests.ConnectionError, requests.exceptions.RequestException) as e:
#        print "There was a problem deleting"
#        print "    " + str(e)

# Uploading
print 'Uploading files for session %s' % session

queryArgs = {"format": "BIDS_NIFTI", "content": "BIDS_FILES", "tags": "BIDS"}
if workflowId is not None:
    queryArgs["event_id"] = workflowId
if uploadByRef:
    queryArgs["reference"] = os.path.abspath(sessionBidsDir)
    r = sess.put(host + "/data/experiments/%s/resources/BIDS-AZAAC/files" % (session), params=queryArgs)
else:
    queryArgs["extract"] = True
    (t, tempFilePath) = tempfile.mkstemp(suffix='.zip')
    zipdir(dirPath=os.path.abspath(sessionBidsDir), zipFilePath=tempFilePath, includeDirInZip=False)
    files = {'file': open(tempFilePath, 'rb')}
    r = sess.put(host + "/data/experiments/%s/resources/BIDS-AZAAC/files" % (session), params=queryArgs, files=files)
    os.remove(tempFilePath)
r.raise_for_status()

##########
# Clean up input directory
print
print 'Cleaning up %s directory.' % sesdicomdir
rmtree(sesdicomdir)

print
print 'Cleaning up %s directory.' % sessionBidsDir
rmtree(sessionBidsDir)

print
print 'All done with bids conversion.'

