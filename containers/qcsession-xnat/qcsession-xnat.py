from xnatutils.genutils import *
from xnatutils.phantomdefs import *
from xnatutils.phantomReports import *
from xnatutils.standalone_html import *
from shutil import copytree
from bids import BIDSLayout
import nibabel as nib
import numpy as np
import argparse

BIDSVERSION = "1.0.0"

parser = argparse.ArgumentParser(description="Run dcm2bids and pydeface on every file in a session")
parser.add_argument("--host", default="https://cnda.wustl.edu", help="CNDA host", required=True)
parser.add_argument("--user", help="CNDA username", required=True)
parser.add_argument("--password", help="Password", required=True)
parser.add_argument("--session", help="Session ID", required=True)
parser.add_argument("--subject", help="Subject Label", required=False)
parser.add_argument("--session_label", help="session Label",  nargs='?', required=False)
parser.add_argument("--project", help="Project", required=False)
parser.add_argument("--proc_steps", help="additional proc steps",  nargs='?', required=False)
parser.add_argument("--dicomdir", help="Root output directory for DICOM files", required=True)
parser.add_argument("--niftidir", help="Root output directory for NIFTI files", required=True)
parser.add_argument("--workdir", help="working directory for temporary files", required=False,default="/tmp")
parser.add_argument("--bidsconfig", help="path to BIDS config file", required=False, default="dcm2bids/bidsconfig")
parser.add_argument("--bidsaction", help="path to BIDS action file", required=False, default="dcm2bids/bidsaction")
parser.add_argument("--overwrite", help="Overwrite NIFTI files if they exist")
parser.add_argument("--upload-by-ref", help="Upload \"by reference\". Only use if your host can read your file system.")
parser.add_argument("--cleanup", help="Attempt to clean up temporary files")
parser.add_argument("--debugmode", help="Attempt to clean up temporary files")
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
debugmode = isTrue(args.debugmode)
dicomdir = args.dicomdir
niftidir = args.niftidir
workdir = args.workdir
workflowId = args.workflowId
uploadByRef = isTrue(args.upload_by_ref)
additionalArgs = unknown_args if unknown_args is not None else []

bidsaction=args.bidsaction
bidsconfig=args.bidsconfig

builddir = os.getcwd()

# create niftidir
if not os.access(niftidir, os.R_OK):
    os.mkdir(niftidir)

bidsdir = niftidir + "/BIDS"
if not os.access(bidsdir, os.R_OK):
    os.mkdir(bidsdir)

# Clunky - we are just going to overide /dicoms for now so we can debug better
dicomdir = niftidir + "/DICOMS"
if not os.access(dicomdir, os.R_OK):
    os.mkdir(dicomdir)


BIDS_RESOURCE_FOLDER='BIDS-AACAZ'
LOG_RESOURCE_FOLDER='LOGS-AACAZ'
CONFIG_RESOURCE_FOLDER='CONFIG-AACAZ'
EDDYQC_RESOURCE_FOLDER='EDDYQC-AACAZ'
PHANTOMROI_RESOURCE_FOLDER='PHANTOMROI-AACAZ'
PHANTOMQC_RESOURCE_FOLDER='PHANTOMQC-AACAZ'

LOGFOLDER=os.path.join(niftidir,LOG_RESOURCE_FOLDER)
if not os.access(LOGFOLDER, os.R_OK):
    os.mkdir(LOGFOLDER)

CONFIGFOLDER=os.path.join(niftidir,CONFIG_RESOURCE_FOLDER)
if not os.access(CONFIGFOLDER, os.R_OK):
    os.mkdir(CONFIGFOLDER)

# set up log file
TIMESTAMP = datetime.datetime.now().strftime("%m%d%y%H%M%S%p")
LOGFILENAME = 'aacazxnat_' + TIMESTAMP + '.log'
LOGFILENAME = os.path.join(LOGFOLDER,LOGFILENAME)
LOGFILE = open(LOGFILENAME,'w+')

# Set up session
sess = startSession(args.user,args.password)

if project is None:
    logtext (LOGFILE,"Get project for session ID %s." % session)
    project = getProjectFromSession(sess, session, host)
logtext (LOGFILE,"Project: " + project)

if subject is None:
    logtext (LOGFILE,"Get subject ID and subject Label for session ID %s." % session)
    subjectvals = getSubjectFromSession(sess, session, host)
    subject = subjectvals[0]
    subject_label = subjectvals[1]
else:
    subject_label = getSubjectLabelFromSubject(sess,subject,host)
    
logtext (LOGFILE,"Subject ID: " + subject)
logtext (LOGFILE,"Subject Label: " + subject_label)

# Make Subject bids compatible - 10/23/2021 CU
bids_subject_label = subject_label
bids_subject_label=bids_subject_label.replace('_','')
# ensure that hyphens not present in session label - 11/10/2021 CU
bids_subject_label=bids_subject_label.replace('-','')
logtext (LOGFILE,"BIDS Subject Label: " + bids_subject_label)

bids_session_label = session_label
session_label = getSessionLabel(sess, session,host)
logtext (LOGFILE,"Session Label: " + session_label)

if bids_session_label is None or isspace(bids_session_label):   
    # Now default to the last tag instead of the first - 10/23/2021 CU
    bids_session_label = session_label.split('_')[-1]

# ensure that hyphens and underscore not present in session label - 11/10/2021 CU
bids_session_label = bids_session_label.replace('_','')
bids_session_label = bids_session_label.replace('-','')
logtext (LOGFILE,"BIDS Session Label: " + bids_session_label)

    
subdicomdir = os.path.join(dicomdir, subject)
if not os.path.isdir(subdicomdir):
    logtext (LOGFILE,'creating DICOM/subject directory %s.' % subdicomdir)
    os.mkdir(subdicomdir)
        
#make dicom dir unique - might not be truly necessary
sesdicomdir = os.path.join(subdicomdir, session)
if not os.path.isdir(sesdicomdir):
    logtext (LOGFILE,'creating DICOM/subject/session directory %s.' % sesdicomdir)
    os.mkdir(sesdicomdir)

subjectBidsDir=os.path.join(bidsdir,bids_subject_label)
if not os.path.isdir(subjectBidsDir):
    logtext (LOGFILE,'creating BIDS/subject directory %s.' % subjectBidsDir)
    os.mkdir(subjectBidsDir)

sessionBidsDir=os.path.join(subjectBidsDir,bids_session_label)
if not os.path.isdir(sessionBidsDir):
    logtext (LOGFILE,'creating BIDS/subject/session directory %s.' % sessionBidsDir)
    os.mkdir(sessionBidsDir)


# massive try block to fail gracefully
try:
    # CPU 2/15/2022 - provode functionlaity to non-anonymize phantom bids json
    PHANTOM = False

    PHANTOM_NAMES = [ 'ACR']
    # Download and convert Dicoms to BIDS format
    CURRSTEP='initialisation'
    if CURRSTEP in proc_steps:  
    # Get list of scan ids
        #only run if overwrite flag set or eddy_quad files  not previously created
        os.chdir("/tmp")

        # find step-specific parameters
        step_info=''
        proc_steps_list=proc_steps.split(",")
        for step_item in proc_steps_list:
            if CURRSTEP in step_item:
                step_info = step_item
                break

        PHANTOM_NAMES = []
        SUBSTEP=':phantomnames'
        SUBSTEPOUT=SUBSTEP + '='
        if SUBSTEP in step_info:
            if SUBSTEPOUT in step_info:
                if step_info.split(SUBSTEPOUT)[1]:
                    commandInput=step_info.split(SUBSTEPOUT)[1].split(':')[0]
                    PHANTOM_NAMES=commandInput.split('|')

        SUBSTEP=':isphantom'
        if SUBSTEP in step_info:
            PHANTOM=True
            logtext (LOGFILE,'initialisation:isphantom override set. Phantom pipeline will be run.')

        # number of records to display in phantom report
        MAXRECS = 3
        SUBSTEP=':maxrecs'
        SUBSTEPOUT=SUBSTEP + '='
        if SUBSTEP in step_info:
            if SUBSTEPOUT in step_info:
                if step_info.split(SUBSTEPOUT)[1]:
                    MAXRECS=int(step_info.split(SUBSTEPOUT)[1].split(':')[0].strip())
                    logtext (LOGFILE,'initialisation:maxrecs display %s records in phantom report.' % (str(MAXRECS)))
                else:
                    logtext (LOGFILE,'initialisation:maxrecs parameter missing optional location information. Using default value %s.' % (str(MAXRECS)))


    for PHANTOM_NAME in PHANTOM_NAMES:
        if PHANTOM_NAME in subject_label:
            PHANTOM = True
            logtext (LOGFILE,'initialisation:phantomnames phantom match found for {} in {}. Phantom pipeline will be run.'.format(PHANTOM_NAME,subject_label))
            break

    # Download and convert Dicoms to BIDS format
    CURRSTEP='bidsconvert'
    if CURRSTEP in proc_steps:  
    # Get list of scan ids
        #only run if overwrite flag set or eddy_quad files  not previously created
        os.chdir("/tmp")

        # find step-specific parameters
        step_info=''
        proc_steps_list=proc_steps.split(",")
        for step_item in proc_steps_list:
            if CURRSTEP in step_item:
                step_info = step_item
                break


        SUBSTEP=':defacename'
        DEFACENAME={}
        SUBSTEPOUT=SUBSTEP + '='
        if SUBSTEP in step_info:
            if SUBSTEPOUT in step_info:
                if step_info.split(SUBSTEPOUT)[1]:
                    commandInput=step_info.split(SUBSTEPOUT)[1].split(':')[0]
                    if '>' in commandInput:
                        entityParams=commandInput.split('|')
                        for entityParam in entityParams:
                            ENTITY=entityParam.split('>')[0].strip()
                            ENTITYVALUE=entityParam.split('>')[1].strip()
                            DEFACENAME[ENTITY]=ENTITYVALUE

        BYPASS_DICOMS = False
        BYPASS_DEFACE = False
        BYPASS_CONFIG = False
        BYPASS_ACTION = False
        SUBSTEP=':bypass'
        SUBSTEPOUT=SUBSTEP + '='
        if SUBSTEP in step_info:
            if SUBSTEPOUT in step_info:
                if step_info.split(SUBSTEPOUT)[1]:
                    commandInput=step_info.split(SUBSTEPOUT)[1].split(':')[0]
                    bypassParams=commandInput.split('|')
                    for bypassParam in bypassParams:
                            if bypassParam == "dicoms":
                                BYPASS_DICOMS = True
                            if bypassParam == "deface":
                                BYPASS_DEFACE = True
                            if bypassParam == "config":
                                BYPASS_CONFIG = True
                            if bypassParam == "action":
                                BYPASS_ACTION = True

        DEFACE_REPLACE=False
        SUBSTEP=':defacereplace'
        if SUBSTEP in step_info:
            DEFACE_REPLACE=True
            logtext (LOGFILE,'bidsconvert:deface_replace set. Pydeface will replace anatomicals with defaced versions.')

        NOSESSION=False
        SUBSTEP=':nosession'
        if SUBSTEP in step_info:
            NOSESSION=True
            sessionBidsDir = subjectBidsDir
            logtext (LOGFILE,'No session specified. creating BIDS output at directory %s.' % sessionBidsDir)
        else:
            sessionBidsDir=os.path.join(subjectBidsDir,"ses-"+bids_session_label)
            if not os.path.isdir(sessionBidsDir):
                logtext (LOGFILE,'creating BIDS/subject/session directory %s.' % sessionBidsDir)
                os.mkdir(sessionBidsDir)

        SUBSTEP=':output'
        SUBSTEPOUT=SUBSTEP + '='
        if SUBSTEP in step_info:
            if SUBSTEPOUT  in step_info:
                if step_info.split(SUBSTEPOUT)[1]:
                    BIDS_RESOURCE_FOLDER=step_info.split(SUBSTEPOUT)[1].split(':')[0].strip()
                    logtext (LOGFILE,'bidsconvert:output set to %s.' % BIDS_RESOURCE_FOLDER)
                else:
                    logtext (LOGFILE,'bidsconvert:output parameter not set. Syntax is bidsconvert:output=<FOLDERNAME>')
            else:
                logtext (LOGFILE,'bidsconvert:output parameter not set. Syntax is bidsconvert:output=<FOLDERNAME>')
        else:
            logtext (LOGFILE,'BIDS output will be stored at default location of %s.' % BIDS_RESOURCE_FOLDER)

        SUBSTEP=':backup'
        BACKUP_FOLDER="Backup_" + BIDS_RESOURCE_FOLDER
        SUBSTEPOUT=SUBSTEP + '='
        if SUBSTEP in step_info:
            if SUBSTEPOUT in step_info:
                if step_info.split(SUBSTEPOUT)[1]:
                    BACKUP_FOLDER=step_info.split(SUBSTEPOUT)[1].split(':')[0].strip()
                    logtext (LOGFILE,'bidsconvert:backup of %s set to %s.' % (BIDS_RESOURCE_FOLDER, BACKUP_FOLDER))
                else:
                    logtext (LOGFILE,'bidsconvert:backup parameter missing optional location information. Using default locaton %s.' % BACKUP_FOLDER)

            if checkSessionResource(BIDS_RESOURCE_FOLDER, session, host, sess):
                backupLoc=backupFolder(session,workflowId, BIDS_RESOURCE_FOLDER, BACKUP_FOLDER, LOGFILE, LOGFILENAME, host,sess)
                logtext (LOGFILE, "backed up " + BIDS_RESOURCE_FOLDER + " to " + backupLoc)
            else:
                logtext (LOGFILE,'%s not created yet. Nothing to backup' % BIDS_RESOURCE_FOLDER)

        DO_COPY_CONFIG = False
        CONFIG_RESOURCE_FOLDER_COPY = CONFIG_RESOURCE_FOLDER
        SUBSTEP=':resourcecopy'
        SUBSTEPOUT=SUBSTEP + '='
        if SUBSTEP in step_info:
            DO_COPY_CONFIG = True
            if SUBSTEPOUT in step_info:
                if step_info.split(SUBSTEPOUT)[1]:
                    CONFIG_RESOURCE_FOLDER_COPY=step_info.split(SUBSTEPOUT)[1].split(':')[0].strip()
                    logtext (LOGFILE,'bidsconvert:resourcecopy copy dcm2bids_config and dcm2bids_action to %s.' % (CONFIG_RESOURCE_FOLDER_COPY))
                else:
                    logtext (LOGFILE,'bidsconvert:backup parameter missing optional location information. Using default locaton %s.' % CONFIG_RESOURCE_FOLDER_COPY)

        SUBSTEP=':resourceconfig'
        RESOURCE_CONFIG=False
        SUBSTEPOUT=SUBSTEP + '='
        if SUBSTEP in step_info:
            if SUBSTEPOUT in step_info:
                if step_info.split(SUBSTEPOUT)[1]:
                    RESOURCE_CONFIG=True
                    RESOURCE_CONFIG_FILE=step_info.split(SUBSTEPOUT)[1].split(':')[0].strip()
                    logtext (LOGFILE,'bidsconvert:resourceconfig file %s will be obtained from folder %s.' % (RESOURCE_CONFIG_FILE, CONFIG_RESOURCE_FOLDER))
                else:
                    logtext (LOGFILE,'bidsconvert:resourceconfig parameter missing location information ')
            else:
                logtext (LOGFILE,'bidsconvert:resourceconfig parameter missing location information ')

        SUBSTEP=':resourceaction'
        RESOURCE_ACTION=False
        SUBSTEPOUT=SUBSTEP + '='
        if SUBSTEP in step_info:
            if SUBSTEPOUT in step_info:
                if step_info.split(SUBSTEPOUT)[1]:
                    RESOURCE_ACTION=True
                    RESOURCE_ACTION_FILE=step_info.split(SUBSTEPOUT)[1].split(':')[0].strip()
                    logtext (LOGFILE,'bidsconvert:resourceaction file %s will be obtained from folder %s.' % (RESOURCE_ACTION_FILE, CONFIG_RESOURCE_FOLDER))
                else:
                    logtext (LOGFILE,'bidsconvert:resourceaction parameter missing location information ')
            else:
                logtext (LOGFILE,'bidsconvert:resourceaction parameter missing location information ')

     
        resourceExists = checkSessionResource(BIDS_RESOURCE_FOLDER, session, host, sess)
        if not resourceExists or overwrite:
            logtext (LOGFILE,"Get scan list for session ID %s." % session)
            r = get(sess, host + "/data/experiments/%s/scans" % session, params={"format": "json"})
            scanRequestResultList = r.json()["ResultSet"]["Result"]
            scanIDList = [scan['ID'] for scan in scanRequestResultList]
            seriesDescList = [scan['series_description'] for scan in scanRequestResultList]  # { id: sd for (scan['ID'], scan['series_description']) in scanRequestResultList }
            logtext (LOGFILE,'Found scans %s.' % ', '.join(scanIDList))
            logtext (LOGFILE,'Series descriptions %s' % ', '.join(seriesDescList))
            
            # Fall back on scan type if series description field is empty
            if set(seriesDescList) == set(['']):
                seriesDescList = [scan['type'] for scan in scanRequestResultList]
                logtext (LOGFILE,'Fell back to scan types %s' % ', '.join(seriesDescList))
            

            if BYPASS_DICOMS:
                scanIDList=[]
                seriesDescList=[]
            # Cheat and reverse scanid and seriesdesc lists so numbering is in the right order
            for scanid, seriesdesc in zip(reversed(scanIDList), reversed(seriesDescList)):
                print
                logtext (LOGFILE,'Beginning process for scan %s.' % scanid)
                os.chdir(builddir)
            
                # Get scan resources
                logtext (LOGFILE,"Get scan resources for scan %s." % scanid)
                r = get(sess, host + "/data/experiments/%s/scans/%s/resources" % (session, scanid), params={"format": "json"})
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
                    r = get(sess, host + "/data/experiments/%s/scans/%s/resources" % (session, scanid), params={"format": "json"})
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
            
                r = get(sess, filesURL, params={"format": "json"})
                # I don't like the results being in a list, so I will build a dict keyed off file name
                dicomFileDict = {dicom['Name']: {'URI': host + dicom['URI']} for dicom in r.json()["ResultSet"]["Result"]}
            
                # Have to manually add absolutePath with a separate request
                r = get(sess, filesURL, params={"format": "json", "locator": "absolutePath"})
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
                        download(name, pathDict, sess)
            
                os.chdir(builddir)
                logtext (LOGFILE,'Done downloading for scan %s.' % scanid)
            


            USE_ADMIN_CONFIG = True
            if RESOURCE_CONFIG:
                dcm2bids_config=os.path.join(bidsdir,RESOURCE_CONFIG_FILE)
                fileexists=downloadProjectfile (CONFIG_RESOURCE_FOLDER, project, bidsdir, RESOURCE_CONFIG_FILE, True, False, host , sess)
                if fileexists:
                    USE_ADMIN_CONFIG = False
                    DO_CONFIG=True
                    logtext(LOGFILE,"Resource action file %s successfully obtained from %s" % (RESOURCE_CONFIG_FILE, CONFIG_RESOURCE_FOLDER))
                    if PHANTOM:
                        with open(dcm2bids_config,'r') as infile:
                            config=json.load(infile)
                        config["dcm2niixOptions"]="-b y -ba n -z y -f '%3s_%f_%p_%t'"
                        with open(dcm2bids_config, 'w') as outfile:
                            json.dump(config, outfile)                 
                else:
                    DO_CONFIG=False
                    USE_ADMIN_CONFIG=True
                    logtext(LOGFILE,"Resource config file %s not found at %s. Defaulting to system action file." % (RESOURCE_CONFIG_FILE, CONFIG_RESOURCE_FOLDER))


            if USE_ADMIN_CONFIG:
                logtext (LOGFILE,"Get project BIDS dcm2bids map")
                r = sess.get(host + "/data/projects/%s/config/%s" % (project,bidsconfig), params={"contents": True})
                if r.ok:
                    config = r.json()
                    #CPU 2/15/2022 -  Non-anonymize phantom bids json
                    if PHANTOM:
                        config["dcm2niixOptions"]="-b y -ba n -z y -f '%3s_%f_%p_%t'"
                        
                    dcm2bids_config=os.path.join(bidsdir,'dcm2bids_config.json')
                    with open(dcm2bids_config, 'w') as outfile:
                        json.dump(config, outfile)
                        DO_CONFIG=True
                else:
                    logtext (LOGFILE,"Could not read project BIDS map")
                    DO_CONFIG=False

            if DO_COPY_CONFIG:
                logtext (LOGFILE,"Getting project BIDS dcm2bids map for bidsconvert:resourcecopy")
                r = sess.get(host + "/data/projects/%s/config/%s" % (project,bidsconfig), params={"contents": True})
                if r.ok:
                    config_copy = r.json()
                    dcm2bids_config_copy=os.path.join(CONFIGFOLDER,'dcm2bids_config.json')
                    with open(dcm2bids_config_copy, 'w') as outfile_copy:
                        json.dump(config_copy, outfile_copy)
                else:
                    logtext (LOGFILE,"Could not read project BIDS config map")


            if DO_CONFIG and not BYPASS_CONFIG:
                if overwrite:
                    if NOSESSION:
                        dcm2bids_command = "dcm2bids -d {} -p {} -c {} -o {} --clobber".format(sesdicomdir, bids_subject_label, dcm2bids_config, sessionBidsDir ).split()
                    else:
                        dcm2bids_command = "dcm2bids -d {} -p {} -s {} -c {} -o {} --clobber".format(sesdicomdir, bids_subject_label, bids_session_label, dcm2bids_config, sessionBidsDir ).split()
                else:
                    if NOSESSION:
                        dcm2bids_command = "dcm2bids -d {} -p {} -c {} -o {}".format(sesdicomdir, bids_subject_label, dcm2bids_config, sessionBidsDir ).split()
                    else:
                        dcm2bids_command = "dcm2bids -d {} -p {} -s {} -c {} -o {}".format(sesdicomdir, bids_subject_label, bids_session_label, dcm2bids_config, sessionBidsDir ).split()
                logtext(LOGFILE, ' '.join(dcm2bids_command))
                logtext(LOGFILE, str(subprocess.check_output(dcm2bids_command)))
         
            #delete temporary folder
            if cleanup:
                tmpBidsDir=os.path.join(sessionBidsDir,'tmp_dcm2bids')
                if os.path.exists(tmpBidsDir):
                    logtext(LOGFILE,'Cleaning up %s directory.' % tmpBidsDir)
                    rmtree(tmpBidsDir)

            # perform deface
            createDatasetDescription(sessionBidsDir, project)
            layout = BIDSLayout(sessionBidsDir)
            T1w=layout.get(suffix='T1w', extension='nii.gz')
            for t1w in T1w:
                T1WDEFACESAME=False
                t1wpath=t1w.path
                t1wentity = layout.parse_file_entities(t1wpath)
                t1wjsonentity = t1wentity.copy()
                t1wjsonentity["extension"]="json"
                t1wjsonfiles = layout.get(return_type='file', **t1wjsonentity)
                if t1wjsonfiles:
                    t1wjson = t1wjsonfiles[0]
                else:
                    t1wjson = None
                if len(DEFACENAME) > 0:
                    for item in DEFACENAME:
                        t1wentity[item]=DEFACENAME[item]
                    outpath=os.path.join(sessionBidsDir, layout.build_path(t1wentity))
                    if outpath == t1wpath:
                        T1WDEFACESAME = True
                        if not DEFACE_REPLACE:
                            BACKUPT1W = t1wpath.split(".nii")[0] + "_backup.nii.gz"
                            logtext(LOGFILE,"pydeface: original and defaced file have the same name. Saving backup of original to %s" % BACKUPT1W )
                            subprocess.check_output(['cp',t1wpath, BACKUPT1W])


                    t1wjsonentity = t1wentity.copy()
                    t1wjsonentity["extension"]="json"
                    DEFACEJSON = os.path.join(sessionBidsDir, layout.build_path(t1wjsonentity))
                    deface_command = "pydeface --force {} --outfile {}".format(t1wpath,outpath).split()
                else:
                    DEFAULTDEFACE = t1wpath.split(".nii")[0] + "_deface.nii.gz"
                    DEFACEJSON = t1wpath.split(".nii")[0] + "_deface.json"
                    deface_command = "pydeface --force {} --outfile {}".format(t1wpath, DEFAULTDEFACE).split()

                if not BYPASS_DEFACE and not PHANTOM:
                    logtext(LOGFILE,"Executing command: " + " ".join(deface_command))
                    logtext(LOGFILE,subprocess.check_output(deface_command))

                    if t1wjson and DEFACEJSON and not T1WDEFACESAME:
                        logtext (LOGFILE, "copying %s to %s" %(t1wjson, DEFACEJSON))
                        subprocess.check_output(['cp',t1wjson, DEFACEJSON])


                    if DEFACE_REPLACE and not T1WDEFACESAME:
                        logtext(LOGFILE,"Removing anatomical %s" % t1wpath)
                        os.remove(t1wpath)
                        if t1wjson:
                            os.remove(t1wjson)

            DO_ACTION=False

            USE_ADMIN_ACTION = True
            if RESOURCE_ACTION:
                dcm2bids_action=os.path.join(bidsdir,RESOURCE_ACTION_FILE)
                fileexists=downloadProjectfile (CONFIG_RESOURCE_FOLDER, project, bidsdir, RESOURCE_ACTION_FILE, True, False, host, sess)
                if fileexists:
                    DO_ACTION=True
                    USE_ADMIN_ACTION = False
                    logtext(LOGFILE,"Resource action file %s successfully obtained from %s" % (RESOURCE_ACTION_FILE, CONFIG_RESOURCE_FOLDER))
                    with open(dcm2bids_action, 'r') as outfile:
                        action = json.load(outfile)

                else:
                    DO_ACTION=False
                    USE_ADMIN_ACTION=True
                    logtext(LOGFILE,"Resource action file %s not found at %s. Defaulting to system action file." % (RESOURCE_ACTION_FILE, CONFIG_RESOURCE_FOLDER))


            if USE_ADMIN_ACTION:
                logtext (LOGFILE,"Get project BIDS bidsaction map")
                r = sess.get(host + "/data/projects/%s/config/%s" % (project,bidsaction), params={"contents": True})
                if r.ok:
                    DO_ACTION=True
                    action = r.json()
                    dcm2bids_action=os.path.join(bidsdir,'dcm2bids_action.json')
                    with open(dcm2bids_action, 'w') as outfile:
                        json.dump(action, outfile)
                else:
                    logtext (LOGFILE,"Could not read project BIDS action map")
                    DO_ACTION=False

            if DO_COPY_CONFIG:
                logtext (LOGFILE,"Get project BIDS bidsaction map for bidsconvert:resourcecopy")
                r = sess.get(host + "/data/projects/%s/config/%s" % (project,bidsaction), params={"contents": True})
                if r.ok:
                    action_copy = r.json()
                    dcm2bids_action_copy=os.path.join(CONFIGFOLDER,'dcm2bids_action.json')
                    with open(dcm2bids_action_copy, 'w') as outfile_copy:
                        json.dump(action_copy, outfile_copy)
                else:
                    logtext (LOGFILE,"Could not read project BIDS action map")


            if DO_ACTION and not BYPASS_ACTION:

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
                            entities['subject']=bids_subject_label

                        sessionbids=list(filter(lambda x: "ses-" in x, labels))
                        if sessionbids:
                            sessionValue=sessionbids[0].split('-')[1]
                            entities['session']=sessionValue
                        elif not NOSESSION:
                            entities['session']=bids_session_label

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
                        entities['subject']=bids_subject_label
                        if not NOSESSION:
                            entities['session']=bids_session_label

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
                        entities['subject']=bids_subject_label
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
            # Upload results
            logtext (LOGFILE,'Preparing to upload files for session %s.' % session)

            if DO_COPY_CONFIG:
                logtext (LOGFILE, "Uploading configuration files to %s" % CONFIG_RESOURCE_FOLDER )
                if checkProjectResource(CONFIG_RESOURCE_FOLDER, project, sess):
                    logtext (LOGFILE, "%s already exists. Will back it up and then delete it." % CONFIG_RESOURCE_FOLDER )
                    backupLoc = backupProjectFolder(project,workflowId,CONFIG_RESOURCE_FOLDER , "backup_" + CONFIG_RESOURCE_FOLDER , LOGFILE, LOGFILENAME,host,sess)
                    logtext (LOGFILE, "moved  " + CONFIG_RESOURCE_FOLDER + " to " + backupLoc)
                    deleteFolder(workflowId,"/data/projects/%s/resources/%s" % (project,CONFIG_RESOURCE_FOLDER), LOGFILE,host, sess)     
                uploadfiles (workflowId , "CONFIG_JSON", "CONFIG_FILES" ,"CONFIG", CONFIGFOLDER, "/data/projects/%s/resources/%s/files" % (project,CONFIG_RESOURCE_FOLDER_COPY),host , sess,uploadByRef,args)

            if resourceExists and overwrite and not BYPASS_CONFIG:
                logtext(LOGFILE, 'Deleting existing %s folder for %s' % (BIDS_RESOURCE_FOLDER, session))
                deleteFolder(workflowId, "/data/experiments/%s/resources/%s" % (session,BIDS_RESOURCE_FOLDER) , LOGFILE, host,sess)

            logtext(LOGFILE, 'Uploading BIDS files for session %s to location %s' % (session,BIDS_RESOURCE_FOLDER))
            LOGFILE.flush()
            subprocess.check_output(['cp',LOGFILENAME,sessionBidsDir])      
            uploadfiles (workflowId , "BIDS_NIFTI", "BIDS_FILES" ,"BIDS", sessionBidsDir, "/data/experiments/%s/resources/%s/files" % (session,BIDS_RESOURCE_FOLDER) ,host,sess,uploadByRef,args)

        else:
            message = 'Looks like Dcm2bids has already been run. If you want to rerun then set overwrite flag to True.'
            logtext (LOGFILE, message)



    # perform miscellaneous file operations
    if 'eddyqc' in proc_steps and not PHANTOM:
        os.chdir("/tmp")

        # find step-specific parameters
        step_info=''
        proc_steps_list=proc_steps.split(",")
        for step_item in proc_steps_list:
            if 'eddyqc:' in step_item:
                step_info = step_item
                break

        sliceorder='json'
        eddy_params=''

        EDDYQCFOLDER=os.path.join(niftidir,EDDYQC_RESOURCE_FOLDER)
        if not os.access(EDDYQCFOLDER, os.R_OK):
            os.mkdir(EDDYQCFOLDER)

        resourceExists = checkSessionResource(EDDYQC_RESOURCE_FOLDER, session, host,sess)
        if not resourceExists or overwrite:

            if not os.listdir(sessionBidsDir):
                    bidsprepare(project, session, sessionBidsDir,BIDS_RESOURCE_FOLDER,host,sess)

            eddyworkdir=os.path.join(EDDYQCFOLDER,'work')
            if not os.path.isdir(eddyworkdir):
                os.mkdir(eddyworkdir)
            eddyQCOutdir=os.path.join(EDDYQCFOLDER,'EDDYQC')
            if not os.path.isdir(eddyQCOutdir):
                os.mkdir(eddyQCOutdir)

            layout = BIDSLayout(sessionBidsDir)
            
            entities={}
            entities['extension']=['nii','nii.gz']
            entities['datatype']='dwi'
            dwifiles=layout.get(return_type='file', **entities)
            # run for each dwifile
            for dwi in dwifiles:
                dwijson=layout.get_metadata(dwi)
                dwi_entity = layout.parse_file_entities(dwi)
                dwi_entity['extension']='json'
                dwijsonfile=layout.get(return_type='file', **dwi_entity)[0]

                bvec=layout.get_bvec(dwi)
                bval=layout.get_bval(dwi)
                rpe=layout.get_fieldmap(dwi)['epi']
                rpejson=layout.get_metadata(rpe)

                rpe_entity = layout.parse_file_entities(rpe)
                rpe_entity['extension']='json'
                rpe_entity.pop("fmap")
                rpejsonfile=layout.get(return_type='file', **rpe_entity)[0]

                dwiImage=nib.load(dwi)
                rpeImage=nib.load(rpe)
                numslices=dwiImage.header['dim'][3]
                numrpe=rpeImage.header['dim'][4]

        
                #hardcode the slspec file creation
                dwimif=os.path.join(eddyworkdir,os.path.basename(dwi).split('_dwi')[0] + '_dwi.mif')
                slspec=dwimif.split('_dwi')[0] + '_slspec.txt'
            
                if sliceorder == 'oddasc':
                    oddtxt=[str(x) for x in list(range(0,numslices,2))]
                    eventxt=[str(x) for x in list(range(1,numslices,2))]
                    slspectxt='\n'.join(oddtxt) + '\n' + '\n'.join(eventxt) +'\n'
                    f=open(slspec, 'w+')
                    f.write (slspectxt)
                    f.close()
                elif sliceorder == 'json':
                    mbf=dwijson['MultibandAccelerationFactor']
                    slicetimes=dwijson['SliceTiming']
                    slicearray=np.array(slicetimes)
                    sort_index=np.argsort(slicearray)
                    dimy=int(len(slicearray)/mbf)
                    spec=np.reshape(sort_index,(dimy,mbf))
                    for i in range(len(spec)):
                        spec[i].sort()
                    np.savetxt(slspec,spec,fmt='%d')

                # create mrtrix dwi file
                
                createmif_command="mrconvert -force {} -json_import {} -fslgrad {} {} {}".format(dwi,dwijsonfile,bvec,bval,dwimif).split()
                print(subprocess.check_output(createmif_command))

                rpemif=os.path.join(eddyworkdir,os.path.basename(rpe).split('_epi')[0] + '_epi.mif')
     
                rpestub=rpemif.split('.mif')[0]
                rpebval=rpestub + '.bval'
                rpebvec=rpestub + '.bvec'

                bvecs=np.zeros((3,numrpe))
                np.savetxt(rpebvec,bvecs,fmt='%d')
                bvals=np.zeros(numrpe)
                np.savetxt(rpebval,bvals,fmt='%d')

                
                createmif_command="mrconvert -force {} -json_import {} -fslgrad {} {} {}".format(rpe,rpejsonfile,rpebvec,rpebval,rpemif).split()
                print(subprocess.check_output(createmif_command))


                alldwimif=dwimif.split('.mif')[0] + "_all.mif"
                concat_command="mrcat -force {} {} -axis 3 {}".format(dwimif,rpemif,alldwimif).split()
                print(subprocess.check_output(concat_command))

                scratchdir=os.path.join(EDDYQCFOLDER,'scratch')
                if not os.path.isdir(scratchdir):
                        os.mkdir(scratchdir)

                preprocdwimif=dwimif.split('.mif')[0] + "_all_preproc.mif"
                eddy_command='dwifslpreproc {} {} -scratch {} -eddy_slspec {} -eddyqc_all {} -nocleanup -rpe_header -eddy_options " --slm=linear --repol --cnr_maps --ol_type=both --niter=8 --fwhm=10,6,4,2,0,0,0,0 --mporder=8 --s2v_niter=8"'.format(alldwimif,preprocdwimif,scratchdir,slspec,eddyQCOutdir )

                print ('Running eddy for session %s: \n%s' % (session, eddy_command))
                os.system(eddy_command)
         
              
                # Uploading EDDYQC files
                if resourceExists and overwrite:
                    logtext(LOGFILE, 'Deleting existing %s folder for %s' % (EDDYQC_RESOURCE_FOLDER, session))
                    deleteFolder(workflowId, "/data/experiments/%s/resources/%s" % (session,EDDYQC_RESOURCE_FOLDER) , LOGFILE, host,sess)

                print ('Uploading EDDYQC files for session %s.' % session)
                uploadfiles (workflowId , "EDDYQC_NIFTI", "EDDYQC_FILES" ,"EDDYQC", eddyQCOutdir, "/data/experiments/%s/resources/%s/files" % (session,EDDYQC_RESOURCE_FOLDER) ,host,sess,uploadByRef,args)
                if cleanup and checkSessionResource(EDDYQC_RESOURCE_FOLDER, session, host,sess):
                    logtext (LOGFILE, 'Cleaning up %s directory.' % EDDYQCFOLDER)
                    rmtree(EDDYQCFOLDER)

        else:
            message = 'Looks like EDDYQC has already been run for session %s. If you want to rerun then set overwrite flag to True.' % session
            print (message)
            logtext (LOGFILE, message)

    if 'phantomqc' in proc_steps and not PHANTOM:
        message = 'phantomqc in processing steps but Subject Label {} not identified as a phantom. phantom names are {}'.format(subject_label, str(PHANTOM_NAMES))
        logtext (LOGFILE, message)


    if 'phantomqc' in proc_steps and PHANTOM: 
        os.chdir("/tmp")

        # find step-specific parameters
        step_info=''
        proc_steps_list=proc_steps.split(",")
        for step_item in proc_steps_list:
            if 'phantomqc:' in step_item:
                step_info = step_item
                break

        # add functionality to change these if necessary
        PHANTOM_BASE_ANAT='base'
        PHANTOM_BASE_FUNC='base'
        PHANTOM_BASE_ROI='anat_rois.tsv'
        PHANTOM_FUNC_ROI='func_rois.tsv'
        n_procs = 3

        PHANTOMQCFOLDER=os.path.join(niftidir,PHANTOMQC_RESOURCE_FOLDER)
        if not os.access(PHANTOMQCFOLDER, os.R_OK):
            os.mkdir(PHANTOMQCFOLDER)

        resourceExists = checkSessionResource(PHANTOMQC_RESOURCE_FOLDER, session, host,sess)
        if not resourceExists or overwrite:

            if checkSessionResource(BIDS_RESOURCE_FOLDER, session, host,sess):
                if not os.listdir(sessionBidsDir) or overwrite:
                    bidsprepare(project, session, sessionBidsDir,BIDS_RESOURCE_FOLDER,host,sess)

                phantomroidir=os.path.join(PHANTOMQCFOLDER,'roidir')
                if not os.path.isdir( phantomroidir):
                    os.mkdir(phantomroidir)

                if checkProjectResource(PHANTOMROI_RESOURCE_FOLDER, project, host,sess):
        
                    filesDownloaded=downloadProjectfiles(PHANTOMROI_RESOURCE_FOLDER, project, phantomroidir, True, host , sess)
        
                    layout = BIDSLayout(sessionBidsDir)
        
                    anatfile_current=layout.get(suffix='T1w',extension='nii.gz')[0].path
                    funcfile_current=layout.get(task='rest',extension='nii.gz')[0].path
                    anat_current_datetime = layout.get_metadata(anatfile_current)["AcquisitionDateTime"]
                    func_current_datetime = layout.get_metadata(funcfile_current)["AcquisitionDateTime"]
        
                    anatfile_base=glob.glob(os.path.join(phantomroidir,'*ses-{}*T1w*.nii.gz'.format(PHANTOM_BASE_ANAT)))[0]
                    funcfile_base=glob.glob(os.path.join(phantomroidir,'*ses-{}*task-rest*bold*.nii.gz'.format(PHANTOM_BASE_FUNC)))[0]


                    # workflow root name
                    wf_root='acrmed_qc_wf'
                               
                    # base outputdir
                    output_dir=os.path.join(PHANTOMQCFOLDER,'outputdir')
                    if not os.path.isdir( output_dir):
                        os.mkdir(output_dir)
                
                    # Run anatomical pipeline on current session using base rois
                    prefix='anat_current'
                    wf_name='{}_{}'.format(prefix,wf_root)
                
                    #split out signal and noise masks
                    base_anat_roi=os.path.join(phantomroidir, PHANTOM_BASE_ROI)
                    with open(base_anat_roi) as f:
                        lines = f.readlines()
                
                    signal_roi_list = []
                    noise_roi_list = []
                    index=0
                    for roi in lines:
                       signal_roi = roi.split()[0]
                       noise_roi = roi.split()[1]
                       signal_roi_list.insert(index, signal_roi)
                       noise_roi_list.insert(index, noise_roi)
                       index=index+1
                
                    current_anat_wf = create_anat_wf(wf_name,output_dir,anatfile_current, anatfile_base, signal_roi_list, noise_roi_list, phantomroidir, prefix)
                    current_anat_wf.write_graph(graph2use='flat')
                    res_anat = current_anat_wf.run('MultiProc', plugin_args={'n_procs': n_procs})
                    ###################################################### 
                    # get anatomical json
                    anat_report_json = collateAnatJson(lines,output_dir, wf_name, anat_current_datetime)   
                
                    # Run functional pipeline on current session using base rois
                    prefix='func_current'
                    wf_name='{}_{}'.format(prefix,wf_root)

                    #split out signal and noise masks
                    base_func_roi=os.path.join(phantomroidir, PHANTOM_FUNC_ROI)
                    with open(base_func_roi) as f:
                        lines = f.readlines()
                
                    signal_roi_list = []
                    noise_roi_list = []
                    index=0
                    for roi in lines:
                       signal_roi = roi.split()[0]
                       noise_roi = roi.split()[1]
                       signal_roi_list.insert(index, signal_roi)
                       noise_roi_list.insert(index, noise_roi)
                       index=index+1
                
                    current_func_wf = create_func_wf(wf_name,output_dir,funcfile_current, funcfile_base, signal_roi_list, noise_roi_list, phantomroidir, prefix)
                    current_func_wf.write_graph(graph2use='flat')
                    res_func = current_func_wf.run('MultiProc', plugin_args={'n_procs': n_procs})
                
                    logtext(LOGFILE, "Completed Phantom Processing Pipeline.")
                    #########################################################################
                    # get functional  json
                    func_report_json = collateFuncJson(lines,output_dir, wf_name, func_current_datetime)
                
                    ## save final report
                    final_report_json={}
                    final_report_json["structural"]=anat_report_json["structural"]
                    final_report_json["functional"]=func_report_json["functional"]
                    final_report_file = os.path.join(output_dir, "{}_{}_finalreport.json".format(subject_label, session_label))
                    with open(final_report_file, 'w') as outfile:
                        json.dump(final_report_json, outfile, indent=2)


                    # generate html report
                    logtext (LOGFILE,"Get session specific information for %s." % session)
                    sessionRequest = get(sess, host + "/data/experiments/%s" % session, params={"format":"json","handler": "values" , "columns": "Date"})
                    sessionDateString = sessionRequest.json()["ResultSet"]["Result"][0]["Date"]

                    report_dir=os.path.join(PHANTOMQCFOLDER,'reportdir')
                    if not os.path.isdir( report_dir):
                        os.mkdir(report_dir)

                    report_json_dir=os.path.join(PHANTOMQCFOLDER,'jsons')
                    if not os.path.isdir( report_json_dir):
                        os.mkdir(report_json_dir)

                    report_image_dir=os.path.join(report_dir,'images')
                    if not os.path.isdir( report_image_dir):
                        os.mkdir(report_image_dir)


                    refdt = datetime.datetime.strptime(sessionDateString,'%Y-%m-%d')
                    filedown = downloadSubjectSessionfiles (PHANTOMQC_RESOURCE_FOLDER, project, subject, report_json_dir, True, host,sess,bump=True,target="finalreport.json",exactmatch=False, refdate=refdt)
                    reportjson = glob.glob(os.path.join(report_json_dir,'*/*.json'))

                    reportexists = [ ele for ele in reportjson if session in ele ]
                    if len(reportexists) == 0:
                        reportjson.append(final_report_file)
                    reportdict = getSortedReportSet(reportjson, MAXRECS)

                    style_source = "/src/style.css"
                    style_dest = os.path.join(report_dir,'style.css')
                    fileCopy(style_source,style_dest)

                    CURRENTDIR=os.getcwd()
                    os.chdir(report_dir)

                    doc = createPhantomQCReport(MAXRECS,'./style.css', './images', reportdict)

                    final_report_html = os.path.join(report_dir, "{}_{}_phantom_finalreport.html".format(subject_label, session_label))
                    final_report_inline_html = os.path.join(output_dir, "{}_{}_phantom_finalreport_inline.html".format(subject_label, session_label))
                    with open(final_report_html, 'w') as file:
                        file.write(doc.render())
                    make_html_images_inline(final_report_html, final_report_inline_html)

                    os.chdir(CURRENTDIR)

                    copytree(report_dir, os.path.join(output_dir, 'htmlreport'))


                    # Uploading PHANTOMQC files
                    if resourceExists and overwrite:
                        logtext(LOGFILE, 'Deleting existing %s folder for %s' % (PHANTOMQC_RESOURCE_FOLDER, session))
                        deleteFolder(workflowId,"/data/experiments/%s/resources/%s" % (session,PHANTOMQC_RESOURCE_FOLDER) , LOGFILE, host,sess)

                    logtext (LOGFILE, 'Uploading PHANTOMQC files for session %s.' % session)
                    uploadfiles (workflowId , "PHANTOMQC_NIFTI", "PHANTOMQC_FILES" ,"PHANTOMQC", output_dir, "/data/experiments/%s/resources/%s/files" % (session,PHANTOMQC_RESOURCE_FOLDER) ,host,sess,uploadByRef,args)
                    if cleanup and checkSessionResource(BIDS_RESOURCE_FOLDER, session, host,sess):
                        logtext (LOGFILE, 'Cleaning up %s directory.' % PHANTOMQCFOLDER)
                        rmtree(PHANTOMQCFOLDER)


                else:
                    message = '[ERROR: phantomqc ] phantom roi  files have not been created yet for  project %s. These need to be uploaded manually.' % project
                    logtext (LOGFILE, message)
            else:
                message = '[ERROR: phantomqc ] Bids files have not been created yet for  %s. Run bidsconvert then rerun.' % subject
                logtext (LOGFILE, message)
              

        else:
            message = 'Looks like Phantom QC  has already been run for session %s. If you want to rerun then set overwrite flag to True.' % session
            logtext (LOGFILE, message)




    if 'filetools' in proc_steps: 
    # Get list of scan ids
        #only run if overwrite flag set or eddy_quad files  not previously created
        os.chdir("/tmp")

        # find step-specific parameters
        step_info=''
        proc_steps_list=proc_steps.split(",")
        for step_item in proc_steps_list:
            if 'filetools:' in step_item:
                step_info = step_item
                break


        SUBSTEP=':move'
        SUBSTEPOUT=SUBSTEP + '='
        if SUBSTEP in step_info:
            if SUBSTEPOUT in step_info:
                if step_info.split(SUBSTEPOUT)[1]:
                    commandInput=step_info.split(SUBSTEPOUT)[1].split(':')[0]
                    if '>' in commandInput:
                        INPUT_FOLDER=commandInput.split('>')[0].strip()
                        OUTPUT_FOLDER=commandInput.split('>')[1].strip()
                        logtext (LOGFILE,'filetools:move input folder set to %s and output folder set to %s.' % (INPUT_FOLDER, OUTPUT_FOLDER))
                        if checkSessionResource(INPUT_FOLDER, session, host, sess):
                            if OUTPUT_FOLDER:
                                moveLoc = backupFolder(session,workflowId,INPUT_FOLDER, OUTPUT_FOLDER, LOGFILE, LOGFILENAME,host,sess)
                                logtext (LOGFILE, "moved  " + INPUT_FOLDER + " to " + moveLoc)
                                deleteFolder(workflowId,"/data/experiments/%s/resources/%s" % (session,INPUT_FOLDER), LOGFILE,host, sess)                    
                            else:
                                logtext (LOGFILE,'Output destination not defined. Cannot move.')
                        else:
                            logtext (LOGFILE,'%s does not exist.Cannot perform move.' % INPUT_FOLDER)
                    else:
                        logtext (LOGFILE,'filetools:move missing > in syntax. Cannot move.')
                else:
                    logtext (LOGFILE,'filetools:move syntax error. Cannot move.')
            else:
                logtext (LOGFILE,'filetools:move missing = in syntax. Cannot move.')


        SUBSTEP=':copy'
        SUBSTEPOUT=SUBSTEP + '='
        if SUBSTEP in step_info:
            if SUBSTEPOUT in step_info:
                if step_info.split(SUBSTEPOUT)[1]:
                    commandInput=step_info.split(SUBSTEPOUT)[1].split(':')[0]
                    if '>' in commandInput:
                        INPUT_FOLDER=commandInput.split('>')[0].strip()
                        OUTPUT_FOLDER=commandInput.split('>')[1].strip()
                        logtext (LOGFILE,'filetools:copy input folder set to %s and output folder set to %s.' % (INPUT_FOLDER, OUTPUT_FOLDER))
                        if checkSessionResource(INPUT_FOLDER,session, host, sess):
                            if OUTPUT_FOLDER:
                                copyLoc = backupFolder(session,workflowId,INPUT_FOLDER, OUTPUT_FOLDER, LOGFILE, LOGFILENAME, host,sess)
                                logtext (LOGFILE, "copied  " + INPUT_FOLDER + " to " + copyLoc)
                            else:
                                logtext (LOGFILE,'Output destination not defined. Cannot copy.')
                        else:
                            logtext (LOGFILE,'%s does not exist.Cannot perform copy.' % INPUT_FOLDER)
                    else:
                        logtext (LOGFILE,'filetools:copy missing > in syntax. Cannot copy.')
                else:
                    logtext (LOGFILE,'filetools:copy syntax error. Cannot copy.')
            else:
                logtext (LOGFILE,'filetools:copy missing = in syntax. Cannot copy.')

     

    if cleanup:
        logtext (LOGFILE, 'Cleaning up %s directory.' % bidsdir)
        rmtree(bidsdir)

    if cleanup:
        logtext (LOGFILE, 'Cleaning up %s directory.' % dicomdir)
        rmtree(dicomdir)

    if cleanup:
        logtext (LOGFILE, 'Cleaning up /tmp directory.')
        rmtmp_command="rm -rf /tmp*"
        os.system(rmtmp_command)
        os.mkdir("/tmp")

    logtext (LOGFILE, 'All done with session processing.')
except Exception as e:
    logtext (LOGFILE, 'Exception thrown:')
    logtext (LOGFILE, str(e))
    raise
finally:
    LOGFILE.flush()
    # merge old log files with current log file
    if not debugmode:
        logtext(LOGFILE, 'Uploading LOG files for session %s to location %s' % (session, LOG_RESOURCE_FOLDER))
        LOGFILE.flush()
        try: 
            downloadSessionfiles (LOG_RESOURCE_FOLDER, session, LOGFOLDER, True, host,sess)
            if checkSessionResource(LOG_RESOURCE_FOLDER, session, host,sess):
            	deleteFolder(workflowId,"/data/experiments/%s/resources/%s" % (session,LOG_RESOURCE_FOLDER), LOGFILE ,host, sess)
            uploadfiles (workflowId , "LOG_TXT", "LOG_FILES" ,"LOG", LOGFOLDER, "/data/experiments/%s/resources/%s/files" % (session,LOG_RESOURCE_FOLDER) ,host,sess,uploadByRef,args)
        except Exception as e:
            logtext (LOGFILE, 'Exception thrown in Finally Block.')
            logtext (LOGFILE, str(e))
    LOGFILE.close()
