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
from datetime import date

#########################################################
#  removed locatedbids() and collateTargetParticipants()
#   These relied on pandas and pybids which was clashing
#   witgh OS used for bidaspp-setup
#   This is a bit of a hack - look for more unifying solution later.
###############################################################


BIDSVERSION = "1.0.0"

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

def uploadfiles (wfId, FORMAT, CONTENT, TAGS, outpath, hostpath, host,sess,uploadByRef,args):
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
def uploadfile (wfId, FORMAT, CONTENT, TAGS, outpath, hostpath, host, sess,uploadByRef):
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
def deletefile (workflowId,hostpath, log, host,sess):
    try:
        queryArgs={}
        if workflowId is not None:
            queryArgs["event_id"] = workflowId
        r = sess.delete(host + hostpath, params=queryArgs)
        r.raise_for_status()
    except (requests.ConnectionError, requests.exceptions.RequestException) as e:
        logtext (log,"There was a problem deleting file " + hostpath )
        logtext (log,"    " + str(e))

def deleteFolder (workflowId,hostpath, log, host,sess):
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
    subprocess.check_output(['cp','-f',logfilename,tempdir])
    uploadfiles (wfId, FORMAT, CONTENT, TAGS, tempdir, "/data/experiments/%s/resources/%s/files" % (session, foldername),host,sess)
    rmtree(tempdir)
    return foldername


def backupProjectFolder(project,wfId,collectionFolder, backupLoc, log, logfilename, host, sess):
        if not os.path.isdir("/tmp"):
                os.mkdir("/tmp")
        if checkProjectResource(backupLoc, project,host, sess):
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
        subprocess.check_output(['cp','-f',logfilename,tempdir])
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
        if resCollection == collectionFolder:
            if  bidsTreeFolders[-1] == resName:
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
                        print("PROBLEM downloading {}. This file has been skipped.".format(resName))
    return bidsTreeList


def downloadSessionfilesFiltered (collectionFolder, session, outputDir, doit, host, sess,bump=False,target=None,exactmatch=False,retainFolderTree=True,exactFolder=None):
        
    if exactFolder is not None:
        exactMatch = False
        target = None
        retainFolderTree = True


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
        if resCollection == collectionFolder:
            if  bidsTreeFolders[-1] == resName:
                folderLoc = [ ind  for ind, ele in enumerate(bidsTreeFolders[0:-1]) if  ele == exactFolder ]
                if (target is None and exactFolder is None) or (exactmatch and resName == target) or (not exactmatch and target is not None and target in resName) or (len(folderLoc) > 0 and exactFolder is not None):
                    if bump:
                        bidsTreeFolders.insert(0,session)
                    bidsTreeList.append('/'.join(bidsTreeFolders))
                    newdir=outputDir
                    if doit:
                        if retainFolderTree:
                            for dir in bidsTreeFolders[0:-1]:
                                newdir=os.path.join(newdir,dir)
                                if not os.path.isdir(newdir):
                                    os.mkdir(newdir)
                        elif bump:
                            newdir=os.path.join(newdir,session)
                            if not os.path.isdir(newdir):
                                os.mkdir(newdir)

                        os.chdir(newdir)
                        try:
                            download(resName,resourceListValue,sess)
                        except:
                            print("PROBLEM downloading {}. This file has been skipped.".format(resName))
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
   

def downloadAllSessionfiles (collectionFolder, project, outputDir, doit, host,sess,bump=False):
    if not os.path.isdir(outputDir):
         os.mkdir(outputDir)
    bidsTreeList=[]
    #obtain all the sessions for a project
    sessionList = get(sess,host + "/data/projects/%s/experiments" %project, params={"format":"json"})
    sessionListJson = sessionList.json()["ResultSet"]["Result"]
    for sessionListValue in sessionListJson:
        sessionAccession = sessionListValue['ID']
        resourceList=get(sess,host + "/data/experiments/%s/files" % sessionAccession, params={"format": "json"})
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
            if resCollection == collectionFolder:
                if  bidsTreeFolders[-1] == resName:
                    if bump:
                        bidsTreeFolders.insert(0,sessionAccession)
                    bidsTreeList.append('/'.join(bidsTreeFolders))
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
                            print("PROBLEM downloading {}. This file has been skipped.".format(resName))

    return bidsTreeList


# Very similar to downloadAllSessionFiles but looks for a target file amongst all the session files.
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
            if resCollection == collectionFolder and resName == target:
                if  bidsTreeFolders[-1] == resName:       
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
        if resCollection == collectionFolder:
            if  bidsTreeFolders[-1] == resName:
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


# very similar to downloadProjectFiles but looks for a target file
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
                if resCollection == collectionFolder and resName == target:
                    if  bidsTreeFolders[-1] == resName:
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

def checkSubjectResource (collectionFolder, project, subject, host, sess):
    #check that resource folder exists at the project level
    projectList = get(sess, host + "/data/projects/%s/subjects/%s/resources" % (project,subject) , params={"format":"json"})
    projectListJson = projectList.json()["ResultSet"]["Result"]
    for projectListValue in projectListJson:
        resCollection = projectListValue['label']
        if resCollection == collectionFolder:
            return True
    return False

def downloadSessionDicomsZip(project, subject, session, outputDir, host, sess):
    if not os.path.isdir(outputDir):
        os.mkdir(outputDir)

    os.chdir(outputDir)
    resName=project + '_' + subject + '_' + session + '.zip'
    resourceListValue={}
    resourceListValue['URI']=host + "/data/projects/{}/subjects/{}/experiments/{}/scans/ALL/files?format=zip".format(project,subject,session) 
    resourceListValue['absolutePath']=''
    try:
        download(resName,resourceListValue,sess)
    except:
        print("PROBLEM downloading {}. This file has been skipped.".format(resName))

def downloadSubjectfiles (collectionFolder, project, subject, outputDir, doit, host, sess):
    if not os.path.isdir(outputDir):
        os.mkdir(outputDir)
    bidsTreeList=[]
    resourceList=get(sess, host + "/data/projects/%s/subjects/%s/files" % (project, subject), params={"format": "json"})
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
                        print("PROBLEM downloading {}. This file has been skipped.".format(resName))
    return bidsTreeList

def downloadSubjectSessionfiles (collectionFolder, project, subject, outputDir, doit, host,sess,bump=False,target=None,exactmatch=False,refdate=None):
    if not os.path.isdir(outputDir):
        os.mkdir(outputDir)
    bidsTreeList=[]
    #obtain all the sessions for a project
    sessionList = get(sess,host + "/data/projects/%s/experiments" %project, params={"format":"json"})
    sessionListJson = sessionList.json()["ResultSet"]["Result"]
    for sessionListValue in sessionListJson:
        sessionAccession = sessionListValue['ID']
        sessionSubject = getSubjectFromSession(sess,sessionAccession, host)
        if sessionSubject[0] != subject:
            continue

        sessionDateString = sessionListValue['date']
        sessionDateVals=sessionDateString.split("-")
        sessionDate= datetime.datetime(int(sessionDateVals[0]),int(sessionDateVals[1]),int(sessionDateVals[2]))

        if (refdate is None) or (sessionDate <= refdate):
            resourceList=get(sess,host + "/data/experiments/%s/files" % sessionAccession, params={"format": "json"})
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
                        if (target is None) or (exactmatch and resName == target) or (not exactmatch and target in resName):
                            if bump:
                                bidsTreeFolders.insert(0,sessionAccession)
                            bidsTreeList.append('/'.join(bidsTreeFolders))
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
                                    print("PROBLEM downloading {}. This file has been skipped.".format(resName))
    return bidsTreeList


def downloadAllSessionfilesFiltered (collectionFolder, project, outputDir, doit, host,sess,bump=False,target=None,exactmatch=False,refdate=None,retainFolderTree=True,exactFolder=None):

    if exactFolder is not None:
        bump = True
        exactMatch = False
        target = None
        retainFolderTree = True


    if not os.path.isdir(outputDir):
         os.mkdir(outputDir)
    bidsTreeList=[]
    #obtain all the sessions for a project
    sessionList = get(sess,host + "/data/projects/%s/experiments" %project, params={"format":"json"})
    sessionListJson = sessionList.json()["ResultSet"]["Result"]
    for sessionListValue in sessionListJson:
        sessionAccession = sessionListValue['ID']

        sessionDateString = sessionListValue['date']
        sessionDateVals=sessionDateString.split("-")
        sessionDate= datetime.datetime(int(sessionDateVals[0]),int(sessionDateVals[1]),int(sessionDateVals[2]))

        if (refdate is None) or (sessionDate <= refdate):
            resourceList=get(sess,host + "/data/experiments/%s/files" % sessionAccession, params={"format": "json"})
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
                if resCollection == collectionFolder:
                    if  bidsTreeFolders[-1] == resName:
                        folderLoc = [ ind  for ind, ele in enumerate(bidsTreeFolders[0:-1]) if  ele == exactFolder ]
                        if (target is None and exactFolder is None) or (exactmatch and resName == target) or (not exactmatch and target is not None and target in resName) or (len(folderLoc) > 0 and exactFolder is not None):
                            if bump:
                                bidsTreeFolders.insert(0,sessionAccession)
                            bidsTreeList.append('/'.join(bidsTreeFolders))
                            newdir=outputDir
                            if doit:
                                if retainFolderTree:
                                    for dir in bidsTreeFolders[0:-1]:
                                        newdir=os.path.join(newdir,dir)
                                        if not os.path.isdir(newdir):
                                            os.mkdir(newdir)
                                elif bump:
                                    newdir=os.path.join(newdir,sessionAccession)
                                    if not os.path.isdir(newdir):
                                        os.mkdir(newdir)

                                os.chdir(newdir)
                                try:
                                    download(resName,resourceListValue,sess)
                                except:
                                    print("PROBLEM downloading {}. This file has been skipped.".format(resName))

    return bidsTreeList

#copy down BIDS file for project
def getBids(project, bidsDir, bidsFolder, host, sess,overwrite=True):

    if not os.path.exists(bidsDir):
        os.mkdir(bidsDir)

    filesDownloaded=[]

    if not os.listdir(bidsDir) or overwrite:
        filesDownloaded = downloadAllSessionfiles (bidsFolder, project, bidsDir, True, host,sess)
    # remove all log files
    loggingfiles = glob.glob(os.path.join(bidsDir,"*.log"))
    for loggingfile in loggingfiles:
        os.remove(loggingfile)
    projname=getProjectName(sess, host, project)
    createDatasetDescription(bidsDir, project,projname)

    collateParticipantsTSV(project, bidsDir, bidsFolder, host,sess)

    return filesDownloaded



def getSubjectDemographics(subject, sess, host, session=None):
    # get xnat demographics
    SUBJECT_DEMOGRAPHICS={}

    if subject is None:
        if session is None:
            return SUBJECT_DEMOGRAPHICS
        else:
            subject=get(sess, host + "/data/experiments/%s" % session, params={"format": "json", "handler": "values", "columns": "subject_ID"}).json()["ResultSet"]["Result"][0]['subject_ID']

    results=get(sess, host + "/data/subjects/%s" % subject, params={"format": "json"})
    SUBJECT_DEMOGRAPHICS["gender_xnat"]=""
    try:
        gender_xnat=results.json()['items'][0]['children'][0]['items'][0]['data_fields']['gender']
        SUBJECT_DEMOGRAPHICS["gender_xnat"]=gender_xnat
    except KeyError:
        pass

    SUBJECT_DEMOGRAPHICS["age_xnat"]=""
    try:
        age_xnat=results.json()['items'][0]['children'][0]['items'][0]['data_fields']['age']
        SUBJECT_DEMOGRAPHICS["age_xnat"]=age_xnat
    except KeyError:
        pass

    try:
        dob_xnat=results.json()['items'][0]['children'][0]['items'][0]['data_fields']['dob']
        agedate_xnat=datetime.datetime.strptime(dob_xnat,"%Y-%m-%d")
        age_xnat=getAge(agedate_xnat)
        SUBJECT_DEMOGRAPHICS["age_xnat"]=age_xnat
    except KeyError:
        pass

    try:
        yob_xnat=results.json()['items'][0]['children'][0]['items'][0]['data_fields']['yob']
        agedate_xnat=datetime.datetime.strptime(str(yob_xnat),"%Y")
        age_xnat=getAge(agedate_xnat)
        SUBJECT_DEMOGRAPHICS["age_xnat"]=age_xnat
    except KeyError:
        pass 

    return SUBJECT_DEMOGRAPHICS  

# copy down the BIDS files for just this session
def bidsprepare( project, session,bidsDir, bidsFolder, host,sess, overwrite=True):

    if not os.path.exists(bidsDir):
        os.mkdir(bidsDir)

    if not os.listdir(bidsDir) or overwrite:
        filesDownloaded= downloadSessionfiles (bidsFolder, session, bidsDir, True, host,sess)
    #remove all log files
    loggingfiles = glob.glob(os.path.join(bidsDir,"*.log"))
    for loggingfile in loggingfiles:
        os.remove(loggingfile)

    projname=getProjectName(sess, host, project)
    createDatasetDescription(bidsDir, project, projname)

def createDatasetDescription(bidsDir, proj, projname=None):
    datasetjson=os.path.join(bidsDir,'dataset_description.json')
    if not os.path.exists(datasetjson):
        print("Constructing BIDS dataset description")
        dataset_description=OrderedDict()
        if projname:
            dataset_description['Name'] =projname
        else:
            dataset_description['Name'] =proj            
        dataset_description['XNATProject'] =proj
        dataset_description['BIDSVersion']=BIDSVERSION
        dataset_description['License']=""
        dataset_description['ReferencesAndLinks']=""
        with open(datasetjson,'w') as outfile:
             json.dump(dataset_description,outfile,indent=2)
    else:
        # add XNATProject ID
        with open(datasetjson,'r') as infile:
             dataset_description=json.load(infile)
        if projname:
            dataset_description['Name'] =projname
        else:
            dataset_description['Name'] =proj  
        dataset_description['XNATProject'] =proj
        with open(datasetjson,'w') as outfile:
             json.dump(dataset_description,outfile,indent=2)


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
    if logfile is not None:
        logfile.write(textstring + '\n')

def posttext(logfile, textstr):
    textstring =str(textstr)
    print(textstring)
    if logfile is not None:
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

def getProjectName(sess, host, proj):
    results = get(sess, host + "/data/projects/%s" % proj, params={"format": "json"})
    projectName = results.json()["items"][0]["data_fields"]['name']

    return projectName

def getProjectFromSession(sess, session, host):
    r = get(sess, host + "/data/experiments/%s" % session, params={"format": "json", "handler": "values", "columns": "project"})
    sessionValuesJson = r.json()["ResultSet"]["Result"][0]
    project = sessionValuesJson["project"]
    return project

def getSubjectFromSession(sess, session, host):
    returnvalue=[]
    r = get(sess, host + "/data/experiments/%s" % session, params={"format": "json", "handler": "values", "columns": "project,subject_ID"})
    sessionValuesJson = r.json()["ResultSet"]["Result"][0]
    subjectID = sessionValuesJson["subject_ID"]
    
    subjectLabel=getSubjectLabelFromSubject(sess,subjectID,host)
    returnvalue.append(subjectID)
    returnvalue.append(subjectLabel)
    return returnvalue

def getSubjectLabelFromSubject(sess,subject,host):
    r = get(sess, host + "/data/subjects/%s" % subject, params={"format": "json", "handler": "values", "columns": "label"})
    subjectLabel = r.json()["ResultSet"]["Result"][0]["label"]
    return subjectLabel


def getSessionLabel(sess, session,host):
    r = get(sess, host + "/data/experiments/%s" % session, params={"format": "json", "handler": "values", "columns": "label"})
    sessionValuesJson = r.json()["ResultSet"]["Result"][0]
    session_label = sessionValuesJson["label"]
    return session_label

def getAge(birthdate):
    today = date.today()
    age = today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))
    return age
