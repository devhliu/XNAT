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
from shutil import copy as fileCopy
from shutil import rmtree
from shutil import copytree
from collections import OrderedDict
import requests.packages.urllib3
requests.packages.urllib3.disable_warnings()
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
    if wfId is not None:
        queryArgs["event_id"] = wfId
    if uploadByRef:
        queryArgs["reference"] = os.path.abspath(outpath)
        r = sess.put(host + hostpath, params=queryArgs)
    else:
        queryArgs["extract"] = True
        (t, tempFilePath) = tempfile.mkstemp(suffix='.zip')
        zipdir(dirPath=os.path.abspath(outpath), zipFilePath=tempFilePath, includeDirInZip=False)
        files = {'file': open(tempFilePath, 'rb')}
        #r = sess.put(host + hostpath, params=queryArgs, files=files)
        #with open(tempFilePath, 'rb') as file_stream:
        #    response = requests.put(host + hostpath, verify=False, auth=(args.user, args.password), data=file_stream)
        #file_stream.close()

        #try curl
        curl_command = 'curl -k -u {}:{} -X POST "{}{}?format={}&content={}&tags={}&extract=True" -F "file.zip=@{}" '.format(args.user, args.password,host,hostpath,FORMAT, CONTENT, TAGS, tempFilePath)
        os.system(curl_command)



        os.remove(tempFilePath)
    #r.raise_for_status()

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

    datasetjson=os.path.join(sessionBidsDir,'dataset_description.json');
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
    textstring =  stamp + '  ' + textstr
    print(textstring)
    logfile.write(textstring + '\n')


BIDSVERSION = "1.0.0"

parser = argparse.ArgumentParser(description="Run dcm2niix on every file in a session")
parser.add_argument("command", default="uploadSession", help="uploadSession, downloadSession, uploadProject, downloadProject")
parser.add_argument("xnatfolder", default="DEFAULT-ORBISYS", help="collection name")
parser.add_argument("extDir", default="./", help="source directory")
parser.add_argument("--host", default="https://cnda.wustl.edu", help="CNDA host", required=True)
parser.add_argument("--user", help="CNDA username", required=True)
parser.add_argument("--password", help="Password", required=True)
parser.add_argument("--session", help="Session ID", required=True)
parser.add_argument("--project", help="Project", required=False)
parser.add_argument("--labels", default="DEFAULT,DEFAULT_FILES,DEFAULT", help="label values for uploaded files",  nargs='?', required=False)
parser.add_argument("--overwrite", help="Overwrite NIFTI files if they exist")
parser.add_argument("--upload-by-ref", help="Upload \"by reference\". Only use if your host can read your file system.")
parser.add_argument("--workflowId", help="Pipeline workflow ID")
parser.add_argument('--version', action='version', version='%(prog)s 1')

args, unknown_args = parser.parse_known_args()
host = cleanServer(args.host)

command = args.command
xnatfolder = args.xnatfolder
extDir = args.extDir

session = args.session
project = args.project
labels = args.labels
overwrite = isTrue(args.overwrite)
workflowId = args.workflowId
uploadByRef = isTrue(args.upload_by_ref)

# Set up session
sess = requests.Session()
sess.verify = False
sess.auth = (args.user, args.password)

print ("Session: " + session)

# try an Get project ID and subject ID from session JSON if project is None
print ("Get project and subject ID for session ID %s." % session)
r = get(host + "/data/experiments/%s" % session, params={"format": "json", "handler": "values", "columns": "project,subject_ID"})
sessionValuesJson = r.json()["ResultSet"]["Result"][0]
project = sessionValuesJson["project"] if project is None else project
print ("Project: " + project)

defaultlabels="DEFAULT,DEFAULT_FILES,DEFAULT".split(",")
sublabels = labels.split(",")
for counter, value in enumerate (sublabels):
    if counter > 2:
        continue
    else:
        defaultlabels[counter]=value

if command == 'uploadSession':
    if session is None:
        print("Cannot upload session without a valid session label. Please specify session with --session")
    else:
        uploadfiles (workflowId , defaultlabels[0], defaultlabels[1] ,defaultlabels[2], extDir, "/data/experiments/%s/resources/%s/files" % (session, xnatfolder) )

elif command == 'downloadSession':
    if session is None:
        print("Cannot upload session without a valid session label. Please specify session with --session")
    else:
        filesDownloaded= downloadSessionfiles (xnatfolder, session, extDir, True)
        print(filesDownloaded)
 
elif command == 'uploadProject':
    if project is None:
        print("Cannot upload session without a valid project label. Please specify project with --project")
    else:
        uploadfiles (workflowId , defaultlabels[0], defaultlabels[1] ,defaultlabels[2], extDir, "/data/projects/%s/resources/%s/files" % (project, xnatfolder) )

elif command == 'downloadProject':
    if project is None:
        print("Cannot upload session without a valid project label. Please specify session with -project")
    else:
        filesDownloaded = downloadProjectfiles (xnatfolder, project, extDir, True)
        print(filesDownloaded)
else:
	print("Do not recognize command passed. use uploadSession, downloadSession, uploadProject or downloadProject")





