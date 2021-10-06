#!/usr/local/miniconda/bin/python
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
from shutil import copytree
from nipype.interfaces.dcm2nii import Dcm2nii
from collections import OrderedDict
import requests.packages.urllib3
requests.packages.urllib3.disable_warnings()
from bids import BIDSLayout
import numpy as np
import nibabel as nib
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

def downloadSessionfiles (collectionFolder, session, outputDir, doit ):
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
def bidsprepare(bidsDir):
    os.chdir("/tmp")
    if not os.listdir(bidsDir) or overwrite:
        filesDownloaded= downloadSessionfiles ('BIDS-ORBISYS', session, bidsDir, True)
    createDatasetDescription(bidsDir)

def createDatasetDescription(bidsDir):
    datasetjson=os.path.join(bidsDir,'dataset_description.json');
    if not os.path.exists(datasetjson):
        print("Constructing BIDS dataset description")
        dataset_description=OrderedDict()
        dataset_description['Name'] =project
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

def posttext(logfile, textstr):
    textstring =str(textstr)
    print(textstring)
    logfile.write(textstring + '\n')

def getProjectInfo(project):    
    projectInfo = {}
    #get resource information for project
    projectResourceList=get(host + "/data/projects/%s/files" % project, params={"format": "json"})
    projectResourceListJson = projectResourceList.json()["ResultSet"]["Result"]
    projectInfo[project]=projectResourceListJson

    sessionList = get(host + "/data/projects/%s/experiments" %project, params={"format":"json"})
    sessionListJson = sessionList.json()["ResultSet"]["Result"]
    for sessionListValue in sessionListJson:

        sessionDict={}
        sessionAccession = sessionListValue['ID']
        sessionDict['sessionID']=sessionAccession
        sessionDict['project']=project

        sessionLabel = sessionListValue['label']
        sessionDict['sessionLabel']=sessionLabel

        # get session scans
        r = get(host + "/data/experiments/%s/scans" % sessionAccession, params={"format": "json"})
        scanRequestResultList = r.json()["ResultSet"]["Result"]
        scanIDList = [scan['ID'] for scan in scanRequestResultList]
        seriesDescList = [scan['series_description'] for scan in scanRequestResultList]  # { id: sd for (scan['ID'], scan['series_description']) in scanRequestResultList }

        sessionDict['scanID']=scanIDList
        sessionDict['scanName']=seriesDescList

        # get subject ID details for session
        sessionDetail = get(host + "/data/experiments/%s" % sessionAccession, params={"format": "json", "handler": "values", "columns": "project,subject_ID"})
        sessionValuesJson = sessionDetail.json()["ResultSet"]["Result"][0]
        subjectID = sessionValuesJson["subject_ID"]

        # get subject label
        subjectDetail = get(host + "/data/subjects/%s" % subjectID, params={"format": "json", "handler": "values", "columns": "project,label"})
        subjectValuesJson = subjectDetail.json()["ResultSet"]["Result"][0]
        subjectLabel = subjectValuesJson["label"]

        sessionDict['subjectID']=subjectID
        sessionDict['subjectLabel']=subjectLabel 

        sessionResourceList = get(host + "/data/experiments/%s/files" %sessionAccession, params={"format":"json"})
        sessionResourceListJson = sessionResourceList.json()["ResultSet"]["Result"]
        sessionDict['sessionResources']=sessionResourceListJson

        projectInfo[sessionAccession]=sessionDict

    return projectInfo

BIDSVERSION = "1.0.0"

parser = argparse.ArgumentParser(description="Run dcm2niix on every file in a session")
parser.add_argument("--host", default="https://cnda.wustl.edu", help="CNDA host", required=True)
parser.add_argument("--user", help="CNDA username", required=True)
parser.add_argument("--password", help="Password", required=True)
parser.add_argument("--project", help="project ID", required=True)
parser.add_argument("--subject", help="Subject Label", required=False)
parser.add_argument("--proc_steps", help="additional proc steps",  nargs='?', required=False)
parser.add_argument("--mriqc_params", help="additional mriqc params",  nargs='?', required=False)
parser.add_argument("--fmriprep_params", help="additional fmriprep params",  nargs='?', required=False)
parser.add_argument("--eddy_params", help="additional eddy params",  nargs='?', required=False)
parser.add_argument("--dicomdir", help="Root output directory for DICOM files", required=True)
parser.add_argument("--niftidir", help="Root output directory for NIFTI files", required=True)
parser.add_argument("--overwrite", help="Overwrite NIFTI files if they exist")
parser.add_argument("--upload-by-ref", help="Upload \"by reference\". Only use if your host can read your file system.")
parser.add_argument("--workflowId", help="Pipeline workflow ID")
parser.add_argument('--version', action='version', version='%(prog)s 1')

args, unknown_args = parser.parse_known_args()
host = cleanServer(args.host)
mriqc_params = args.mriqc_params
proc_steps = args.proc_steps
if proc_steps is None:
    proc_steps = ''
if not proc_steps:
	proc_steps = 'report'
fmriprep_params = args.fmriprep_params
eddy_params = args.eddy_params
project = args.project
overwrite = isTrue(args.overwrite)
dicomdir = args.dicomdir
niftidir = args.niftidir
workflowId = args.workflowId
uploadByRef = isTrue(args.upload_by_ref)
dcm2niixArgs = unknown_args if unknown_args is not None else []

bidsdir = niftidir + "/BIDS"

builddir = os.getcwd()

# set up log file
TIMESTAMP = datetime.datetime.now().strftime("%m%d%y%H%M%S%p")
LOGFILENAME = 'xnatSession_' + TIMESTAMP + '.log'
LOGFILENAME = os.path.join(niftidir,LOGFILENAME)
LOGFILE = open(LOGFILENAME,'w+')

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


FSLICENSE=os.path.join(bidsdir,'license.txt')
subprocess.check_output(['cp','/tmp/license.txt',FSLICENSE])


# run report 
if 'report' in proc_steps:
    os.chdir("/tmp")
    OUTFOLDER="REPORT"
    SUFFIX=datetime.datetime.now().strftime("%m%d%y_%H%M%S_%f")
    resourceExists = checkProjectResource(OUTFOLDER, project)

    if resourceExists:
    	OUTFOLDER="{}_".format(OUTFOLDER) + SUFFIX
    	message='Looks like REPORT has already been run for project %s. Results will be stored in %s.' % (project, OUTFOLDER)
    	logtext (LOGFILE, message)


    repOutdir=os.path.join(bidsdir,'REPORT')
    if not os.path.isdir(repOutdir):
       os.mkdir(repOutdir)

    posttext (LOGFILE,'\nProject: %s ' % project)

    #obtain report info
    projectResults=getProjectInfo(project)

    # parse report
    subjectResults={}
    resultList=[]
    # iterate over project results
    for items in projectResults:
    	if items == project:
    		projectResources=projectResults[items]
    		continue
    	subjectLabel=projectResults[items]['subjectLabel']
    	if subjectLabel in subjectResults:
    		subjectResults[subjectLabel].append(projectResults[items])
    	else:
    		subjectResults[subjectLabel]=[]
    		subjectResults[subjectLabel].append(projectResults[items])

    resourceResults=set()
    for resourceValue in projectResources:
    	resCollection = resourceValue['collection']
    	resourceResults.add(resCollection)

    if len(resourceResults) == 0:
    	posttext (LOGFILE,'No project Resource Collections available')
    else:
    	posttext (LOGFILE,'The Following Project Resource Collections available:')

    for resColl in resourceResults:
    	posttext (LOGFILE,'Resource: %s' % resColl)

    for items in sorted(subjectResults):
    	subjectResultsList = subjectResults[items]
    	posttext (LOGFILE,'\nSubject: %s ' % items )
    	for results in subjectResultsList:
    		sessionID=results['sessionID']
    		sessionLabel=results['sessionLabel']
    		posttext (LOGFILE,'\n\tSession: %s ' % sessionLabel )
    		sessionResources=results['sessionResources']
    		sessionResourceResults=set()
    		for resourceValue in sessionResources:
    			resCollection = resourceValue['collection']
    			sessionResourceResults.add(resCollection)

    		if len(sessionResourceResults) == 0:
    			posttext (LOGFILE,'\t\tNo Session Resource Collections available')
    		else:
    			posttext (LOGFILE,'\t\tThe Following Session Resource Collections available:')

    		for resColl in sessionResourceResults:
    			posttext (LOGFILE,'\t\tResource: %s' % resColl)

    		scanID=results['scanID']
    		scanName=results['scanName']
    		posttext (LOGFILE,'\n\t\tThe following scans are available for session')
    		for id, name in zip(scanID,scanName):
    			posttext (LOGFILE,'\t\tScanID: %s \tScanName: %s' % (id,name))

    logtext(LOGFILE,'\nUploading report files for project %s' % project)
    LOGFILE.flush()
    subprocess.check_output(['cp',LOGFILENAME,repOutdir])
    uploadfiles (workflowId , "REPORT_TXT", "REPORT_FILES" ,"REPORT", repOutdir, "/data/projects/%s/resources/%s/files" % (project, OUTFOLDER) )



    
# run group MRIQC
if 'mriqc' in proc_steps:
    os.chdir("/tmp")

    OUTFOLDER="MRIQC-ORBISYS"
    SUFFIX=datetime.datetime.now().strftime("%m%d%y_%H%M%S_%f")
    resourceExists = checkProjectResource(OUTFOLDER, project)

    if resourceExists:
    	OUTFOLDER="{}_".format(OUTFOLDER) + SUFFIX
    	message='Looks like MRIQC has already been run for project %s. Results will be stored in %s.' % (project, OUTFOLDER)
    	logtext (LOGFILE, message)

    mriqcOutdir=os.path.join(bidsdir,'MRIQC')
    if not os.path.isdir(mriqcOutdir):
         os.mkdir(mriqcOutdir)

    projectBidsDir=os.path.join(bidsdir,project)
    if not os.path.isdir(projectBidsDir):
    	os.mkdir(projectBidsDir)
    filesDownloaded = downloadAllSessionfiles ('MRIQC-ORBISYS', project, mriqcOutdir, True)
    mriqc_command = "mriqc {} {} group {}".format(projectBidsDir, mriqcOutdir, mriqc_params).split() 
    logtext(LOGFILE, subprocess.check_output(mriqc_command))

    # no comment
    # Uploading MRIQC files
    logtext(LOGFILE,'Uploading group MRIQC files for project %s' % project)
    LOGFILE.flush()
    subprocess.check_output(['cp',LOGFILENAME,mriqcOutdir])
    uploadfiles (workflowId , "MRIQC_NIFTI", "MRIQC_FILES" ,"MRIQC", mriqcOutdir, "/data/projects/%s/resources/%s/files" % (project, OUTFOLDER) )

    # Clean out tmp directory
    print ('Cleaning up /tmp directory.')
    rmtree("/tmp")
    if not os.path.isdir("/tmp"):
        os.mkdir("/tmp")


if 'eddyqc' in proc_steps:
    os.chdir("/tmp")

    OUTFOLDER="EDDYQC-ORBISYS"
    SUFFIX=datetime.datetime.now().strftime("%m%d%y_%H%M%S_%f")
    resourceExists = checkProjectResource(OUTFOLDER, project)

    if resourceExists:
    	OUTFOLDER="{}_".format(OUTFOLDER) + SUFFIX
    	message='Looks like EDDYQC has already been run for project %s. Results will be stored in %s.' % (project, OUTFOLDER)
    	logtext (LOGFILE, message)

    eddyQuadDirs=''
    eddyQCOutdir=os.path.join(bidsdir,'EDDYQC')
    filesDownloaded = downloadAllSessionfiles ('EDDYQC-ORBISYS', project, eddyQCOutdir, True)

    quadfolders=os.path.join(eddyQCOutdir,'quad_folders.txt')
    eddyQuadDirs='\n'.join([os.path.join(eddyQCOutdir, os.path.dirname(s)) for s in filesDownloaded if 'qc.json' in s])
    f=open(quadfolders, 'w+')
    f.write (eddyQuadDirs)
    f.close()

    message = 'Following directories will be used for SQUAD:\n%s' % eddyQuadDirs
    logtext (LOGFILE, message)

    eddyGroupQCOutdir=os.path.join(eddyQCOutdir,'squad')
    if os.path.exists(eddyGroupQCOutdir):
        rmtree(eddyGroupQCOutdir)
    eddysquad_command = "eddy_squad {} -o {}".format(quadfolders, eddyGroupQCOutdir).split() 
    logtext(LOGFILE, ' '.join(eddysquad_command))
    logtext(LOGFILE, str(subprocess.check_output(eddysquad_command)))
    logtext (LOGFILE, 'Cleaning up /tmp directory.')
    rmtree("/tmp")
    if not os.path.isdir("/tmp"):
        os.mkdir("/tmp")
    # Uploading EDDYQC
    logtext(LOGFILE, 'Uploading group EDDYQC files for project %s' % project)
    LOGFILE.flush()
    subprocess.check_output(['cp',LOGFILENAME,eddyGroupQCOutdir])
    uploadfiles (workflowId , "EDDYQC_NIFTI", "EDDYQC_FILES" ,"EDDYQC", eddyGroupQCOutdir, "/data/projects/%s/resources/%s/files" % (project, OUTFOLDER) )


logtext (LOGFILE, 'Cleaning up %s directory.' % bidsdir)
rmtree(bidsdir)

logtext (LOGFILE, 'Cleaning up %s directory.' % dicomdir)
rmtree(dicomdir)

logtext (LOGFILE, 'All done with session processing.')

LOGFILE.close()
