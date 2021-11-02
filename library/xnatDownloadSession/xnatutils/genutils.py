#!/pyenv/py373bin/python
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


def download(name, pathDict,sess):
    if os.access(pathDict['absolutePath'], os.R_OK):
        try:
            os.symlink(pathDict['absolutePath'], name)
        except:
            fileCopy(pathDict['absolutePath'], name)
            print ('Copied %s.' % pathDict['absolutePath'])
    else:
        with open(name, 'wb') as f:
            r = get(sess, pathDict['URI'], stream=True)

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

def uploadfiles (wfId, FORMAT, CONTENT, TAGS, outpath, hostpath, host,sess):
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

# this function under construction/testing/exploration
def uploadfile (wfId, FORMAT, CONTENT, TAGS, outpath, hostpath, host, sess):
    queryArgs = {"format": FORMAT, "content": CONTENT, "tags": TAGS}
    raiseStatus=False
    if wfId is not None:
        queryArgs["event_id"] = wfId
    if uploadByRef:
        queryArgs["reference"] = os.path.abspath(outpath)
        r = sess.put(host + hostpath, params=queryArgs)
    if raiseStatus:
        r.raise_for_status()

# this function under construction/testing/ex[ploration
def deletefile (hostpath, log, host,sess):
    try:
        queryArgs={}
        if workflowId is not None:
            queryArgs["event_id"] = workflowId
        r = sess.delete(host + hostpath, params=queryArgs)
        r.raise_for_status()
    except (requests.ConnectionError, requests.exceptions.RequestException) as e:
        logtext (log,"There was a problem deleting file " + hostpath )
        logtext (log,"    " + str(e))

def deleteFolder (hostpath, log, host,sess):
    try:
        queryArgs={}
        if workflowId is not None:
            queryArgs["event_id"] = workflowId
        r = sess.delete(host + hostpath, params=queryArgs)
        r.raise_for_status()
    except (requests.ConnectionError, requests.exceptions.RequestException) as e:
        logtext (log,"There was a problem deleting folder " + hostpath )
        logtext (log,"    " + str(e))

def backupFolder(session,wfId,collectionFolder, backupLoc, log, logfilename,host,sess):
    if not os.path.isdir("/tmp"):
        os.mkdir("/tmp")
    if checkSessionResource(backupLoc, session, host, sess):
        BACKUPPREFIX = datetime.datetime.now().strftime("%m%d%y_%H%M%S_%f")
        logtext (log, "location " + backupLoc  + " already exists ")
        foldername = backupLoc + "_" + BACKUPPREFIX
    else:
        foldername=backupLoc

    tempdir="/tmp/" + foldername
    if not os.path.isdir(tempdir):
        os.mkdir(tempdir)
    downloadSessionfiles (collectionFolder, session, tempdir, True, host,sess)
    resourceInfo=getResourceInfo(collectionFolder,session, host,sess)
    FORMAT=resourceInfo['file_format']
    CONTENT=resourceInfo['file_content']
    TAGS=resourceInfo['file_tags']
    logtext(log, 'copying files for folder %s and session %s to location %s' % (collectionFolder, session, foldername))
    log.flush()
    subprocess.check_output(['cp',logfilename,tempdir])
    uploadfiles (wfId, FORMAT, CONTENT, TAGS, tempdir, "/data/experiments/%s/resources/%s/files" % (session, foldername),host,sess)
    rmtree(tempdir)
    return foldername


def backupProjectFolder(project,wfId,collectionFolder, backupLoc, log, logfilename, host, sess):
        if not os.path.isdir("/tmp"):
                os.mkdir("/tmp")
        if checkProjectResource(backupLoc, project,sess):
                BACKUPPREFIX = datetime.datetime.now().strftime("%m%d%y_%H%M%S_%f")
                logtext (log, "location " + backupLoc  + " already exists ")
                foldername = backupLoc + "_" + BACKUPPREFIX
        else:
                foldername=backupLoc

        tempdir="/tmp/" + foldername
        if not os.path.isdir(tempdir):
                os.mkdir(tempdir)
        downloadProjectfiles (collectionFolder, session, tempdir, True, host,sess)
        resourceInfo=getResourceInfo(collectionFolder,session, host,sess)
        FORMAT=resourceInfo['file_format']
        CONTENT=resourceInfo['file_content']
        TAGS=resourceInfo['file_tags']
        logtext(log, 'copying files for folder %s and project %s to location %s' % (collectionFolder, project, foldername))
        log.flush()
        subprocess.check_output(['cp',logfilename,tempdir])
        uploadfiles (wfId, FORMAT, CONTENT, TAGS, tempdir, "/data/projects/%s/resources/%s/files" % (project, foldername),host, sess)
        rmtree(tempdir)
        return foldername



def downloadSessionfiles (collectionFolder, session, outputDir, doit, host, sess):
    if not os.path.isdir(outputDir):
         os.mkdir(outputDir)
    bidsTreeList=[]
    resourceList=get(sess, host + "/data/experiments/%s/files" % session, params={"format": "json"})
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
                    try:
                        download(resName,resourceListValue,sess)
                    except:
                        print("Problems downloading" + resourceListValue['absolutePath'])
    return bidsTreeList

def getResourceInfo(collectionFolder, session, host,sess):
    resourceList=get(sess, host + "/data/experiments/%s/files" % session, params={"format": "json"})
    resourceListJson = resourceList.json()["ResultSet"]["Result"]
    for resourceListValue in resourceListJson:
        resCollection = resourceListValue['collection']
        if resCollection == collectionFolder:
            return resourceListValue

def checkSessionResource (collectionFolder, session, host,sess):
    #check that resource folder exists at the project level
    sessionList = get(sess, host + "/data/experiments/%s/resources" %session, params={"format":"json"})
    sessionListJson = sessionList.json()["ResultSet"]["Result"]
    for sessionListValue in sessionListJson:
        resCollection = sessionListValue['label']
        if resCollection == collectionFolder:
            return True
    return False
   

def downloadAllSessionfiles (collectionFolder, project, outputDir, doit, host,sess):
    if not os.path.isdir(outputDir):
         os.mkdir(outputDir)
    bidsTreeList=[]
    #obtain all the sessions for a project
    sessionList = get(sess, host + "/data/projects/%s/experiments" %project, params={"format":"json"})
    sessionListJson = sessionList.json()["ResultSet"]["Result"]
    for sessionListValue in sessionListJson:
        sessionAccession = sessionListValue['ID']
        resourceList=get(sess, host + "/data/experiments/%s/files" % sessionAccession, params={"format": "json"})
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
                        try:
                            download(resName,resourceListValue,sess)
                        except:
                            print("Problems downloading " + resourceListValue['absolutePath'])

    return bidsTreeList

def downloadSessionfile (collectionFolder, project, outputDir, target,doit, retainFolderTree, host,sess ):
    if not os.path.isdir(outputDir):
         os.mkdir(outputDir)
    bidsTreeList=[]
    #obtain all the sessions for a project
    sessionList = get(sess, host + "/data/projects/%s/experiments" %project, params={"format":"json"})
    sessionListJson = sessionList.json()["ResultSet"]["Result"]
    for sessionListValue in sessionListJson:
        sessionAccession = sessionListValue['ID']
        resourceList=get(sess, host + "/data/experiments/%s/files" % sessionAccession, params={"format": "json"})
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
                if resCollection == collectionFolder and resName == target:
                    bidsTreeList.append(bidsTree)
                    newdir=outputDir
                    if doit:
                        if retainFolderTree:
                            for dir in bidsTreeFolders[0:-1]:
                                newdir=os.path.join(newdir,dir)
                                if not os.path.isdir(newdir):
                                    os.mkdir(newdir)
                        os.chdir(newdir)
                        try:
                            download(resName,resourceListValue,sess)
                        except:
                            print("Problems downloading "+ resourceListValue['absolutePath'])
                        return bidsTreeList

def downloadProjectfiles (collectionFolder, project, outputDir, doit, host , sess):
    if not os.path.isdir(outputDir):
         os.mkdir(outputDir)
    bidsTreeList=[]
    resourceList=get(sess, host + "/data/projects/%s/files" % project, params={"format": "json"})
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
                    download(resName,resourceListValue,sess)
    return bidsTreeList


def downloadProjectfile (collectionFolder, project, outputDir, target, doit, retainFolderTree, host, sess ):
        if not os.path.isdir(outputDir):
                 os.mkdir(outputDir)
        bidsTreeList=[]
        resourceList=get(sess, host + "/data/projects/%s/files" % project, params={"format": "json"})
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
                        if resCollection == collectionFolder and resName == target:
                                bidsTreeList.append(bidsTree)
                                newdir=outputDir
                                if doit:
                                        if retainFolderTree:
                                            for dir in bidsTreeFolders[0:-1]:
                                                    newdir=os.path.join(newdir,dir)
                                                    if not os.path.isdir(newdir):
                                                            os.mkdir(newdir)
                                        os.chdir(newdir)
                                        download(resName,resourceListValue,sess)
        return bidsTreeList




def checkProjectResource (collectionFolder, project, host, sess):
    #check that resource folder exists at the project level
    projectList = get(sess, host + "/data/projects/%s/resources" %project, params={"format":"json"})
    projectListJson = projectList.json()["ResultSet"]["Result"]
    for projectListValue in projectListJson:
        resCollection = projectListValue['label']
        if resCollection == collectionFolder:
            return True
    return False
   

# copy down the BIDS files for just this session
def bidsprepare(bidsDir, bidsFolder, host,sess):
    os.chdir("/tmp")
    if not os.listdir(bidsDir) or overwrite:
        filesDownloaded= downloadSessionfiles (bidsFolder, session, bidsDir, True, host,sess)
    createDatasetDescription(bidsDir)

def createDatasetDescription(bidsDir, proj):
    datasetjson=os.path.join(bidsDir,'dataset_description.json')
    if not os.path.exists(datasetjson):
        print("Constructing BIDS dataset description")
        dataset_description=OrderedDict()
        dataset_description['Name'] =proj
        dataset_description['BIDSVersion']=BIDSVERSION
        dataset_description['License']=""
        dataset_description['ReferencesAndLinks']=""
        with open(datasetjson,'w') as datasetjson:
             json.dump(dataset_description,datasetjson)

def get(sess,url, **kwargs):
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

def getProjectInfo(sess, project, host):    
    projectInfo = {}
    #get resource information for project
    projectResourceList=get(sess, host + "/data/projects/%s/files" % project, params={"format": "json"})
    projectResourceListJson = projectResourceList.json()["ResultSet"]["Result"]
    projectInfo[project]=projectResourceListJson

    sessionList = get(sess, host + "/data/projects/%s/experiments" %project, params={"format":"json"})
    sessionListJson = sessionList.json()["ResultSet"]["Result"]
    for sessionListValue in sessionListJson:

        sessionDict={}
        sessionAccession = sessionListValue['ID']
        sessionDict['sessionID']=sessionAccession
        sessionDict['project']=project

        sessionLabel = sessionListValue['label']
        sessionDict['sessionLabel']=sessionLabel

        # get session scans
        r = get(sess, host + "/data/experiments/%s/scans" % sessionAccession, params={"format": "json"})
        scanRequestResultList = r.json()["ResultSet"]["Result"]
        scanIDList = [scan['ID'] for scan in scanRequestResultList]
        seriesDescList = [scan['series_description'] for scan in scanRequestResultList]  # { id: sd for (scan['ID'], scan['series_description']) in scanRequestResultList }

        sessionDict['scanID']=scanIDList
        sessionDict['scanName']=seriesDescList

        # get subject ID details for session
        sessionDetail = get(sess, host + "/data/experiments/%s" % sessionAccession, params={"format": "json", "handler": "values", "columns": "project,subject_ID"})
        sessionValuesJson = sessionDetail.json()["ResultSet"]["Result"][0]
        subjectID = sessionValuesJson["subject_ID"]

        # get subject label
        subjectDetail = get(sess, host + "/data/subjects/%s" % subjectID, params={"format": "json", "handler": "values", "columns": "project,label"})
        subjectValuesJson = subjectDetail.json()["ResultSet"]["Result"][0]
        subjectLabel = subjectValuesJson["label"]

        sessionDict['subjectID']=subjectID
        sessionDict['subjectLabel']=subjectLabel 

        sessionResourceList = get(sess, host + "/data/experiments/%s/files" %sessionAccession, params={"format":"json"})
        sessionResourceListJson = sessionResourceList.json()["ResultSet"]["Result"]
        sessionDict['sessionResources']=sessionResourceListJson

        projectInfo[sessionAccession]=sessionDict

    return projectInfo

def startSession(user,password):
    sess = requests.Session()
    sess.verify = False
    sess.auth = (user, password)
    return sess

def getProjectFromSession(sess, session, host):
    r = get(sess, host + "/data/experiments/%s" % session, params={"format": "json", "handler": "values", "columns": "project,subject_ID"})
    sessionValuesJson = r.json()["ResultSet"]["Result"][0]
    project = sessionValuesJson["project"]
    return project

def getSubjectFromSession(sess, session, host):
    returnvalue=[]
    r = get(sess, host + "/data/experiments/%s" % session, params={"format": "json", "handler": "values", "columns": "project,subject_ID"})
    sessionValuesJson = r.json()["ResultSet"]["Result"][0]
    subjectID = sessionValuesJson["subject_ID"]
    
    r = get(sess, host + "/data/subjects/%s" % subjectID, params={"format": "json", "handler": "values", "columns": "label"})
    subjectLabel = r.json()["ResultSet"]["Result"][0]["label"]  
    returnvalue.append(subjectID)
    returnvalue.append(subjectLabel)
    return returnvalue

def getSessionLabel(sess, session,host):
    r = get(sess, host + "/data/experiments/%s" % session, params={"format": "json", "handler": "values", "columns": "label"})
    sessionValuesJson = r.json()["ResultSet"]["Result"][0]
    session_label = sessionValuesJson["label"]
    return session_label
