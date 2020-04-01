#!/pyenv/py373bin/python
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
from shutil import copy as fileCopy
from shutil import rmtree
from shutil import copytree
from collections import OrderedDict
import requests.packages.urllib3
requests.packages.urllib3.disable_warnings()
from bids import BIDSLayout
import datetime

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
            print ('Copied %s.' % pathDict['absolutePath'])
    else:
        with open(name, 'wb') as f:
            r = get(pathDict['URI'], stream=True)

            for block in r.iter_content(1024):
                if not block:
                    break

                f.write(block)
        print('Downloaded file %s.' % name)

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

def uploadfiles (wfId, FORMAT, CONTENT, TAGS, outpath, hostpath):
    queryArgs = {"format": FORMAT, "content": CONTENT, "tags": TAGS}
    raiseStatus=False
    if wfId is not None:
        queryArgs["event_id"] = wfId
    if uploadByRef:
        queryArgs["reference"] = os.path.abspath(outpath)
        r = sess.put(host + hostpath, params=queryArgs)
        raiseStatus=True
    else:
        (t, tempFilePath) = tempfile.mkstemp(suffix='.zip')
        zipdir(dirPath=os.path.abspath(outpath), zipFilePath=tempFilePath, includeDirInZip=False)
        curl_command = 'curl -k -u {}:{} -X POST "{}{}?format={}&content={}&tags={}&extract=True" -F "file.zip=@{}" '.format(args.user, args.password,host,hostpath,FORMAT, CONTENT, TAGS, tempFilePath)
        os.chdir("/tmp")
        os.system(curl_command)
        os.remove(tempFilePath)
    if raiseStatus:
        r.raise_for_status()

def deleteFolder (hostpath, log):
    try:
    	queryArgs={}
    	if workflowId is not None:
    		queryArgs["event_id"] = workflowId
    	r = sess.delete(host + hostpath, params=queryArgs)
    	r.raise_for_status()
    except (requests.ConnectionError, requests.exceptions.RequestException) as e:
    	logtext (log,"There was a problem deleting folder " + hostpath )
    	logtext (log,"    " + str(e))

def backupFolder(session,wfId,FORMAT,CONTENT,TAGS,collectionFolder, backupLoc, log):
	if not os.path.isdir("/tmp"):
		os.mkdir("/tmp")
	if checkSessionResource(backupLoc, session):
		BACKUPPREFIX = datetime.datetime.now().strftime("%m%d%y_%H%M%S_%f")
		logtext (log, "backup location " + hostpath  + " already exists ")
		foldername = backupLoc + "_" + BACKUPPREFIX
	else:
		foldername=backupLoc

	logtext (log, "backing up " + collectionFolder " to " + backupLoc)
	tempdir="/tmp/" + foldername
	if not os.path.isdir(tempdir):
		os.mkdir(tempdir)
	downloadSessionfiles (collectionFolder, session, tempdir, True)
	uploadfiles (wfId, FORMAT, CONTENT,TAGS, tempdir, "/data/experiments/%s/resources/%s/files" % (session, foldername))
	rmtree(tempdir)
	return foldername

def downloadSessionfiles (collectionFolder, session, outputDir, doit):
    if not os.path.isdir(outputDir):
         os.mkdir(outputDir)
    bidsTreeList=[]
    resourceList=get(host + "/data/experiments/%s/files" % session, params={"format": "json"})
    resourceListJson = resourceList.json()["ResultSet"]["Result"]
    for resourceListValue in resourceListJson:
        resCollection = resourceListValue['collection']
        resURI = resourceListValue['URI']
        resourceListValue['URI'] = host+resourceListValue['URI']
        resName = resourceListValue['Name']
        resCat_ID = resourceListValue['cat_ID']
        resourceListValue['absolutePath']=''

        bidsTree=resURI.split(resCat_ID + '/files/')[1]
        bidsTreeFolders=bidsTree.split('/')
        if  bidsTreeFolders[-1] == resName:
            if resCollection == collectionFolder:
               bidsTreeList.append(bidsTree)
               newdir=outputDir
               if doit:
                    for dir in bidsTreeFolders[0:-1]:
                        newdir=os.path.join(newdir,dir)
                        if not os.path.isdir(newdir):
                            os.mkdir(newdir)
                    os.chdir(newdir)
                    download(resName,resourceListValue)
    return bidsTreeList

def checkSessionResource (collectionFolder, session):
    #check that resource folder exists at the project level
    sessionList = get(host + "/data/experiments/%s/resources" %session, params={"format":"json"})
    sessionListJson = sessionList.json()["ResultSet"]["Result"]
    for sessionListValue in sessionListJson:
        resCollection = sessionListValue['label']
        if resCollection == collectionFolder:
            return True
    return False
   

def downloadAllSessionfiles (collectionFolder, project, outputDir, doit ):
    if not os.path.isdir(outputDir):
         os.mkdir(outputDir)
    bidsTreeList=[]
    #obtain all the sessions for a project
    sessionList = get(host + "/data/projects/%s/experiments" %project, params={"format":"json"})
    sessionListJson = sessionList.json()["ResultSet"]["Result"]
    for sessionListValue in sessionListJson:
        sessionAccession = sessionListValue['ID']
        resourceList=get(host + "/data/experiments/%s/files" % sessionAccession, params={"format": "json"})
        resourceListJson = resourceList.json()["ResultSet"]["Result"]
        for resourceListValue in resourceListJson:
            resCollection = resourceListValue['collection']
            resURI = resourceListValue['URI']
            resourceListValue['URI'] = host+resourceListValue['URI']
            resName = resourceListValue['Name']
            resCat_ID = resourceListValue['cat_ID']
            resourceListValue['absolutePath']=''

            bidsTree=resURI.split(resCat_ID + '/files/')[1]
            bidsTreeFolders=bidsTree.split('/')
            if  bidsTreeFolders[-1] == resName:
                if resCollection == collectionFolder:
                   bidsTreeList.append(bidsTree)
                   if doit:
                        newdir=outputDir
                        for dir in bidsTreeFolders[0:-1]:
                            newdir=os.path.join(newdir,dir)
                            if not os.path.isdir(newdir):
                                os.mkdir(newdir)
                        os.chdir(newdir)
                        download(resName,resourceListValue)
    return bidsTreeList

def downloadProjectfiles (collectionFolder, project, outputDir, doit ):
    if not os.path.isdir(outputDir):
         os.mkdir(outputDir)
    bidsTreeList=[]
    resourceList=get(host + "/data/projects/%s/files" % project, params={"format": "json"})
    resourceListJson = resourceList.json()["ResultSet"]["Result"]
    for resourceListValue in resourceListJson:
        resCollection = resourceListValue['collection']
        resURI = resourceListValue['URI']
        resourceListValue['URI'] = host+resourceListValue['URI']
        resName = resourceListValue['Name']
        resCat_ID = resourceListValue['cat_ID']
        resourceListValue['absolutePath']=''

        bidsTree=resURI.split(resCat_ID + '/files/')[1]
        bidsTreeFolders=bidsTree.split('/')
        if  bidsTreeFolders[-1] == resName:
            if resCollection == collectionFolder:
               bidsTreeList.append(bidsTree)
               newdir=outputDir
               if doit:
                    for dir in bidsTreeFolders[0:-1]:
                        newdir=os.path.join(newdir,dir)
                        if not os.path.isdir(newdir):
                            os.mkdir(newdir)
                    os.chdir(newdir)
                    download(resName,resourceListValue)
    return bidsTreeList

def checkProjectResource (collectionFolder, project):
    #check that resource folder exists at the project level
    projectList = get(host + "/data/projects/%s/resources" %project, params={"format":"json"})
    projectListJson = projectList.json()["ResultSet"]["Result"]
    for projectListValue in projectListJson:
        resCollection = projectListValue['label']
        if resCollection == collectionFolder:
            return True
    return False
   

# copy down the BIDS files for just this session
def bidsprepare(bidsDir, bidsFolder):
    os.chdir("/tmp")
    if not os.listdir(bidsDir) or overwrite:
        filesDownloaded= downloadSessionfiles (bidsFolder, session, bidsDir, True)
    createDatasetDescription(bidsDir)

def createDatasetDescription(bidsDir, proj):
    datasetjson=os.path.join(bidsDir,'dataset_description.json');
    if not os.path.exists(datasetjson):
        print("Constructing BIDS dataset description")
        dataset_description=OrderedDict()
        dataset_description['Name'] =proj
        dataset_description['BIDSVersion']=BIDSVERSION
        dataset_description['License']=""
        dataset_description['ReferencesAndLinks']=""
        with open(datasetjson,'w') as datasetjson:
             json.dump(dataset_description,datasetjson)

def get(url, **kwargs):
    try:
        r = sess.get(url, **kwargs)
        r.raise_for_status()
    except (requests.ConnectionError, requests.exceptions.RequestException) as e:
        print ("Request Failed")
        print ("    " + str(e))
        sys.exit(1)
    return r

def logtext(logfile, textstr):
    stamp=datetime.datetime.now().strftime("%m-%d-%y %H:%M:%S%p")
    textstring =  str(stamp) + '  ' + str(textstr)
    print(textstring)
    logfile.write(textstring + '\n')


BIDSVERSION = "1.0.0"

parser = argparse.ArgumentParser(description="Run dcm2niix on every file in a session")
parser.add_argument("--host", default="https://cnda.wustl.edu", help="CNDA host", required=True)
parser.add_argument("--user", help="CNDA username", required=True)
parser.add_argument("--password", help="Password", required=True)
parser.add_argument("--session", help="Session ID", required=True)
parser.add_argument("--subject", help="Subject Label", required=False)
parser.add_argument("--session_label", help="session Label",  nargs='?', required=False)
parser.add_argument("--proc_steps", help="additional proc steps",  nargs='?', required=False)
parser.add_argument("--dicomdir", help="Root output directory for DICOM files", required=True)
parser.add_argument("--niftidir", help="Root output directory for NIFTI files", required=True)
parser.add_argument("--workdir", help="working directory for temporary files", required=False,default="/tmp")
parser.add_argument("--bidsconfig", help="path to BIDS config file", required=False, default="dcm2bids/bidsconfig")
parser.add_argument("--bidsaction", help="path to BIDS action file", required=False, default="dcm2bids/bidsaction")
parser.add_argument("--overwrite", help="Overwrite NIFTI files if they exist")
parser.add_argument("--upload-by-ref", help="Upload \"by reference\". Only use if your host can read your file system.")
parser.add_argument("--cleanup", help="Attempt to clean up temporary files")
parser.add_argument("--workflowId", help="Pipeline workflow ID")
parser.add_argument('--version', action='version', version='%(prog)s 1')

args, unknown_args = parser.parse_known_args()
host = cleanServer(args.host)
session = args.session
session_label = args.session_label
proc_steps = args.proc_steps
if proc_steps is None:
    proc_steps = ''
if not proc_steps:
	proc_steps = 'bidsconvert'
subject = args.subject
project = args.project
overwrite = isTrue(args.overwrite)
cleanup = isTrue(args.cleanup)
dicomdir = args.dicomdir
niftidir = args.niftidir
workflowId = args.workflowId
uploadByRef = isTrue(args.upload_by_ref)
additionalArgs = unknown_args if unknown_args is not None else []

bidsaction=args.bidsaction
bidsconfig=args.bidsconfig

bidsdir = niftidir + "/BIDS"

builddir = os.getcwd()

# set up log file
TIMESTAMP = datetime.datetime.now().strftime("%m%d%y%H%M%S%p")
LOGFILENAME = 'xnatSession_' + TIMESTAMP + '.log'
LOGFILENAME = os.path.join(niftidir,LOGFILENAME)
LOGFILE = open(LOGFILENAME,'w+')

BIDS_RESOURCE_FOLDER='BIDS-AACAZ'

# Set up working directory
if not os.access(dicomdir, os.R_OK):
    logtext (LOGFILE,'Making DICOM directory %s' % dicomdir)
    os.mkdir(dicomdir)
if not os.access(niftidir, os.R_OK):
    logtext (LOGFILE,'Making NIFTI directory %s' % niftidir)
    os.mkdir(niftidir)
if not os.access(bidsdir, os.R_OK):
    logtext (LOGFILE,'Making NIFTI BIDS directory %s' % bidsdir)
    os.mkdir(bidsdir)

# Set up session
sess = requests.Session()
sess.verify = False
sess.auth = (args.user, args.password)

if project is None or subject is None:
    # Get project ID and subject ID from session JSON
    logtext (LOGFILE,"Get project and subject ID for session ID %s." % session)
    r = get(host + "/data/experiments/%s" % session, params={"format": "json", "handler": "values", "columns": "project,subject_ID"})
    sessionValuesJson = r.json()["ResultSet"]["Result"][0]
    project = sessionValuesJson["project"] if project is None else project
    subjectID = sessionValuesJson["subject_ID"]
    logtext (LOGFILE,"Project: " + project)
    logtext (LOGFILE,"Subject ID: " + subjectID)

    if subject is None:
        print 
        logtext (LOGFILE,"Get subject label for subject ID %s." % subjectID)
        r = get(host + "/data/subjects/%s" % subjectID, params={"format": "json", "handler": "values", "columns": "label"})
        subject = r.json()["ResultSet"]["Result"][0]["label"]
        logtext (LOGFILE,"Subject label: " + subject)

session_label_all = session_label
if session_label is None:
	# get session label
	r = get(host + "/data/experiments/%s" % session, params={"format": "json", "handler": "values", "columns": "label"})
	sessionValuesJson = r.json()["ResultSet"]["Result"][0]
	session_label_all = sessionValuesJson["label"]
	session_label = session_label_all.split('_')[0]

	
subdicomdir = os.path.join(dicomdir, subject)
if not os.path.isdir(subdicomdir):
    logtext (LOGFILE,'creating DICOM/subject directory %s.' % subdicomdir)
    os.mkdir(subdicomdir)
		
#make dicom dir unique - might not be truly necessary
sesdicomdir = os.path.join(subdicomdir, session_label_all)
if not os.path.isdir(sesdicomdir):
    logtext (LOGFILE,'creating DICOM/subject/session directory %s.' % sesdicomdir)
    os.mkdir(sesdicomdir)

FSLICENSE='/src/license.txt'

subjectBidsDir=os.path.join(bidsdir,"sub-"+subject)
if not os.path.isdir(subjectBidsDir):
    logtext (LOGFILE,'creating BIDS/subject directory %s.' % subjectBidsDir)
    os.mkdir(subjectBidsDir)

if session_label == "nosession":
    sessionBidsDir = subjectBidsDir
else:       
    sessionBidsDir=os.path.join(subjectBidsDir,"ses-"+session_label)
    if not os.path.isdir(sessionBidsDir):
        logtext (LOGFILE,'creating BIDS/subject/session directory %s.' % sessionBidsDir)
        os.mkdir(sessionBidsDir)

# Download and convert Dicoms to BIDS format
if 'bidsconvert' in proc_steps:	
# Get list of scan ids
    #only run if overwrite flag set or eddy_quad files  not previously created
    os.chdir("/tmp")

    # find step-specific parameters
    step_info=''
    proc_steps_list=proc_steps.split(",");
    for step_item in proc_steps_list:
    	if 'bidsconvert:' in step_item:
    		step_info = step_item
    		break

    if ':output' in step_info:
    	if step_info.split(":output")[0].split(":"):
    		BIDS_RESOURCE_FOLDER=step_info.split(":output=")[0].split(":")

    if ':backup' in step_info:
    	if step_info.split(":backup")[0].split(":"):
    		BACKUP_FOLDER=step_info.split(":backup=")[0].split(":")
    	else:
    		BACKUP_FOLDER="Backup_" + BIDS_RESOURCE_FOLDER
    	backupLoc=backupFolder(session,workflowId,"BIDS_NIFTI", "BIDS_FILES" ,"BIDS", BIDS_RESOURCE_FOLDER, BACKUP_FOLDER, LOGFILE)
 
    resourceExists = checkSessionResource(BIDS_RESOURCE_FOLDER, session)
    if not resourceExists or overwrite:
        logtext (LOGFILE,"Get scan list for session ID %s." % session)
        r = get(host + "/data/experiments/%s/scans" % session, params={"format": "json"})
        scanRequestResultList = r.json()["ResultSet"]["Result"]
        scanIDList = [scan['ID'] for scan in scanRequestResultList]
        seriesDescList = [scan['series_description'] for scan in scanRequestResultList]  # { id: sd for (scan['ID'], scan['series_description']) in scanRequestResultList }
        logtext (LOGFILE,'Found scans %s.' % ', '.join(scanIDList))
        logtext (LOGFILE,'Series descriptions %s' % ', '.join(seriesDescList))
        
        # Fall back on scan type if series description field is empty
        if set(seriesDescList) == set(['']):
            seriesDescList = [scan['type'] for scan in scanRequestResultList]
            logtext (LOGFILE,'Fell back to scan types %s' % ', '.join(seriesDescList))
        
        ## Get site- and project-level configs
        #bidsmaplist = []
        
        logtext (LOGFILE,"Get project BIDS dcm2bids map")
        r = sess.get(host + "/data/projects/%s/config/dcm2bids/bidsconfig" % project, params={"contents": True})
        if r.ok:
            config = r.json()
            dcm2bids_config=os.path.join(bidsdir,'dcm2bids_config.json')
            with open(dcm2bids_config, 'w') as outfile:
                json.dump(config, outfile)
        else:
            logtext (LOGFILE,"Could not read project BIDS map")
        
        
        # Cheat and reverse scanid and seriesdesc lists so numbering is in the right order
        for scanid, seriesdesc in zip(reversed(scanIDList), reversed(seriesDescList)):
            print
            logtext (LOGFILE,'Beginning process for scan %s.' % scanid)
            os.chdir(builddir)
        
            # Get scan resources
            logtext (LOGFILE,"Get scan resources for scan %s." % scanid)
            r = get(host + "/data/experiments/%s/scans/%s/resources" % (session, scanid), params={"format": "json"})
            scanResources = r.json()["ResultSet"]["Result"]
            logtext (LOGFILE,'Found resources %s.' % ', '.join(res["label"] for res in scanResources))
        
            ##########
            # Do initial checks to determine if scan should be skipped
            hasNifti = any([res["label"] == "NIFTI" for res in scanResources])  # Store this for later
            if hasNifti and not overwrite:
                logtext (LOGFILE,"Scan %s has a preexisting NIFTI resource, and I am running with overwrite=False. Skipping." % scanid)
                continue
        
            dicomResourceList = [res for res in scanResources if res["label"] == "DICOM"]
            imaResourceList = [res for res in scanResources if res["format"] == "IMA"]
        
            if len(dicomResourceList) == 0 and len(imaResourceList) == 0:
                logtext (LOGFILE,"Scan %s has no DICOM or IMA resource." % scanid)
                # scanInfo['hasDicom'] = False
                continue
            elif len(dicomResourceList) == 0 and len(imaResourceList) > 1:
                logtext (LOGFILE,"Scan %s has more than one IMA resource and no DICOM resource. Skipping." % scanid)
                # scanInfo['hasDicom'] = False
                continue
            elif len(dicomResourceList) > 1 and len(imaResourceList) == 0:
                logtext (LOGFILE,"Scan %s has more than one DICOM resource and no IMA resource. Skipping." % scanid)
                # scanInfo['hasDicom'] = False
                continue
            elif len(dicomResourceList) > 1 and len(imaResourceList) > 1:
                logtext (LOGFILE,"Scan %s has more than one DICOM resource and more than one IMA resource. Skipping." % scanid)
                # scanInfo['hasDicom'] = False
                continue
        
            dicomResource = dicomResourceList[0] if len(dicomResourceList) > 0 else None
            imaResource = imaResourceList[0] if len(imaResourceList) > 0 else None
        
            usingDicom = True if (len(dicomResourceList) == 1) else False
        
            if dicomResource is not None and dicomResource["file_count"]:
                if int(dicomResource["file_count"]) == 0:
                    logtext (LOGFILE,"DICOM resource for scan %s has no files. Checking IMA resource." % scanid)
                    if imaResource["file_count"]:
                        if int(imaResource["file_count"]) == 0:
                            logtext (LOGFILE,"IMA resource for scan %s has no files either. Skipping." % scanid)
                            continue
                    else:
                        logtext (LOGFILE,"IMA resource for scan %s has a blank \"file_count\", so I cannot check it to see if there are no files. I am not skipping the scan, but this may lead to errors later if there are no files." % scanid)
            elif imaResource is not None and imaResource["file_count"]:
                if int(imaResource["file_count"]) == 0:
                    logtext (LOGFILE,"IMA resource for scan %s has no files. Skipping." % scanid)
                    continue
            else:
                logtext (LOGFILE,"DICOM and IMA resources for scan %s both have a blank \"file_count\", so I cannot check to see if there are no files. I am not skipping the scan, but this may lead to errors later if there are no files." % scanid)
        
            ##########
            # Prepare DICOM directory structure
            print
            scanDicomDir = os.path.join(sesdicomdir, scanid)
            if not os.path.isdir(scanDicomDir):
                logtext (LOGFILE,'Making scan DICOM directory %s.' % scanDicomDir)
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
        
                print ('Get IMA resource id for scan %s.' % scanid)
                r = get(host + "/data/experiments/%s/scans/%s/resources" % (session, scanid), params={"format": "json"})
                resourceDict = {resource['format']: resource['xnat_abstractresource_id'] for resource in r.json()["ResultSet"]["Result"]}
        
                if resourceDict["IMA"]:
                    resourceid = resourceDict["IMA"]
                else:
                    logtext (LOGFILE,"Couldn't get xnat_abstractresource_id for IMA file list.")
        
            # Deal with DICOMs
            logtext (LOGFILE,'Get list of DICOM files for scan %s.' % scanid)
        
            if usingDicom:
                filesURL = host + "/data/experiments/%s/scans/%s/resources/DICOM/files" % (session, scanid)
            elif resourceid is not None:
                filesURL = host + "/data/experiments/%s/scans/%s/resources/%s/files" % (session, scanid, resourceid)
            else:
                print ("Trying to convert IMA files but there is no resource id available. Skipping.")
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
            logtext (LOGFILE,"Downloading files for scan %s." % scanid)
            os.chdir(scanDicomDir)
        
            # Check secondary
            # Download any one DICOM from the series and check its headers
            # If the headers indicate it is a secondary capture, we will skip this series.
            dicomFileList = dicomFileDict.items()
              
            ##########
            # Download remaining DICOMs
            for name, pathDict in dicomFileList:
                download(name, pathDict)
        
            os.chdir(builddir)
            logtext (LOGFILE,'Done downloading for scan %s.' % scanid)
        

        if overwrite:
        	if session_label == "nosession":
        		dcm2bids_command = "dcm2bids -d {} -p {} -c {} -o {} --clobber".format(sesdicomdir, subject, dcm2bids_config, sessionBidsDir ).split()
        	else:
        		dcm2bids_command = "dcm2bids -d {} -p {} -s {} -c {} -o {} --clobber".format(sesdicomdir, subject, session_label, dcm2bids_config, sessionBidsDir ).split()
        else:
        	if session_label == "nosession":
        		dcm2bids_command = "dcm2bids -d {} -p {} -c {} -o {}".format(sesdicomdir, subject, dcm2bids_config, sessionBidsDir ).split()
        	else:
        		dcm2bids_command = "dcm2bids -d {} -p {} -s {} -c {} -o {}".format(sesdicomdir, subject, session_label, dcm2bids_config, sessionBidsDir ).split()
        logtext(LOGFILE, ' '.join(dcm2bids_command))
        logtext(LOGFILE, str(subprocess.check_output(dcm2bids_command)))
     
        #delete temporary folder
        tmpBidsDir=os.path.join(sessionBidsDir,'tmp_dcm2bids')
        logtext(LOGFILE,'Cleaning up %s directory.' % tmpBidsDir)
        rmtree(tmpBidsDir)

        # perform deface
        createDatasetDescription(sessionBidsDir, project)
        layout = BIDSLayout(sessionBidsDir)
        T1w=layout.get(suffix='T1w', extension='nii.gz')
        for t1w in T1w:
            t1wpath=t1w.path
            deface_command = "pydeface --force {}".format(t1wpath).split()
            logtext(LOGFILE,"Executing command: " + " ".join(deface_command))
            logtext(LOGFILE,subprocess.check_output(deface_command))

        # Clean out tmp directory
        logtext (LOGFILE,'Cleaning up /tmp directory.')
        rmtree("/tmp")
        if not os.path.isdir("/tmp"):
            os.mkdir("/tmp")

        logtext (LOGFILE,"Get project BIDS bidsaction map")
        r = sess.get(host + "/data/projects/%s/config/dcm2bids/bidsaction" % project, params={"contents": True})
        if r.ok:
            action = r.json()

            try:
            	copyitems = action['copy']
            except KeyError:
            	copyitems = []
            	logtext (LOGFILE, 'No copy items provided.')

            for item in copyitems:
            	entities={}
            	entities['extension']=['nii','nii.gz']
            	try:
            		dataType = item["dataType"]
            		entities['datatype']=dataType
            	except KeyError:
            		dataType = None

            	try:
            		modalityLabel = item["modalityLabel"]
            		entities['suffix']=modalityLabel
            	except KeyError:
            		modalityLabel = None

            	try:
            		customLabels = item["customLabels"]
            		labels = customLabels.split("_")

            		subjectbids=list(filter(lambda x: "sub-" in x, labels))
            		if subjectbids:
            			subjectValue=subjectbids[0].split('-')[1]
            			entities['subject']=subjectValue
            		else:
            			entities['subject']=subject

            		sessionbids=list(filter(lambda x: "ses-" in x, labels))
            		if sessionbids:
            			sessionValue=sessionbids[0].split('-')[1]
            			entities['session']=sessionValue
            		elif session_label != "nosession":
            			entities['session']=session_label

            		task=list(filter(lambda x: "task-" in x, labels))
            		if task:
            			taskValue=task[0].split('-')[1]
            			entities['task']=taskValue

            		acquisition=list(filter(lambda x: "acq-" in x, labels))
            		if acquisition:
            			acquisitionValue=acquisition[0].split('-')[1]
            			entities['acquisition']=acquisitionValue

            		run=list(filter(lambda x: "run-" in x, labels))
            		if run:
            			runValue=run[0].split('-')[1]
            			entities['run']=runValue

            	except KeyError:
            		customLabels= None
            		entities['subject']=subject
            		if session_label != "nosession":
            			entities['session']=session_label

            	files = layout.get(return_type='file', **entities)
            	if files:
            		sourcefile = files[0]
            		entities = layout.parse_file_entities(sourcefile)
            		entities['extension'] = 'json'
            		files = layout.get(return_type='file', **entities)
            		if files:
            			sourcejson = files[0]
            		else:
            			sourcejson = None
            	else:
            		sourcefile = None


            	try:
            		destination = item["destination"]
            	except KeyError:
            		destination = []
            		logtext (LOGFILE, 'No Destination provided for copy')

            	if destination and sourcefile and sourcejson:
            		entities['subject']=subject
            		try:
            			dataType = destination["dataType"]
            			entities['datatype']=dataType
            		except KeyError:
            			dataType = None

            		try:
            			modalityLabel = destination["modalityLabel"]
            			entities['suffix']=modalityLabel
            		except KeyError:
            			modalityLabel = None

            		try:
            			customLabels = destination["customLabels"]
            			labels = customLabels.split("_")

            			sessionbids=list(filter(lambda x: "ses-" in x, labels))
            			if sessionbids:
            				sessionValue=sessionbids[0].split('-')[1]
            				entities['session']=sessionValue

            			task=list(filter(lambda x: "task-" in x, labels))
            			if task:
            				taskValue=task[0].split('-')[1]
            				entities['task']=taskValue
            			else:
            				entities.pop('task', None)

            			acquisition=list(filter(lambda x: "acq-" in x, labels))
            			if acquisition:
            				acquisitionValue=acquisition[0].split('-')[1]
            				entities['acquisition']=acquisitionValue
            			else:
            				entities.pop('acquisition', None)

            			run=list(filter(lambda x: "run-" in x, labels))
            			if run:
            				runValue=run[0].split('-')[1]
            				entities['run']=runValue
            			else:
            				entities.pop('run', None)

            			entities['extension']='nii.gz'
            			outputfile=os.path.join(sessionBidsDir, layout.build_path(entities))
            			if os.path.exists(sourcefile):
            				logtext (LOGFILE, "copying %s to %s" %(sourcefile, outputfile))
            				subprocess.check_output(['cp',sourcefile,outputfile])
            			else:
            				logtext (LOGFILE, "ERROR: %s cannot be found. Check bidsaction file logic." % sourcefile)


            			entities['extension']='json'
            			outputjson=os.path.join(sessionBidsDir, layout.build_path(entities))
            			if os.path.exists(sourcejson):
            				logtext (LOGFILE, "copying %s to %s" %(sourcejson, outputjson))
            				subprocess.check_output(['cp',sourcejson, outputjson])
            			else:
            				logtext (LOGFILE, "ERROR: %s cannot be found. Check bidsaction file logic." % sourcejson)

            		except KeyError:
            			customLabels= None
            	else:
            		logtext (LOGFILE,"Destination or source file could not be found - skipping") 

        else:
            logtext (LOGFILE,"Could not read project BIDS action file - continuing with upload") 	
        ##########
        # Upload results
        logtext (LOGFILE,'Preparing to upload files for session %s.' % session)
        
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
        #        r = sess.delete(host + "/data/experiments/%s/resources/BIDS_RESOURCE_FOLDER" % (session), params=queryArgs)
        #        r.raise_for_status()
        #    except (requests.ConnectionError, requests.exceptions.RequestException) as e:
        #        print "There was a problem deleting"
        #        print "    " + str(e)
        
        # Uploading BIDS
        logtext(LOGFILE, 'Uploading BIDS files for session %s' % session)
        if resourceExists and overwrite:
        	logtext(LOGFILE, 'Deleting existing %s folder for %s' % (BIDS_RESOURCE_FOLDER, session))
        	deleteFolder("/data/experiments/%s/resources/%s" % (session,BIDS_RESOURCE_FOLDER) )
        LOGFILE.flush()
        subprocess.check_output(['cp',LOGFILENAME,sessionBidsDir])
        
        uploadfiles (workflowId , "BIDS_NIFTI", "BIDS_FILES" ,"BIDS", sessionBidsDir, "/data/experiments/%s/resources/%s/files" % (session,BIDS_RESOURCE_FOLDER) )

    else:
        message = 'Looks like Dcm2bids has already been run. If you want to rerun then set overwrite flag to True.'
        logtext (LOGFILE, message)

logtext (LOGFILE, 'Cleaning up %s directory.' % bidsdir)
rmtree(bidsdir)

logtext (LOGFILE, 'Cleaning up %s directory.' % dicomdir)
rmtree(dicomdir)

logtext (LOGFILE, 'All done with session processing.')

LOGFILE.close()
