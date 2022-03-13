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
parser.add_argument("--project", help="Project", required=False)
parser.add_argument("--proc_steps", help="additional proc steps",  nargs='?', required=False)
parser.add_argument("--dicomdir", help="Root output directory for DICOM files", required=True)
parser.add_argument("--niftidir", help="Root output directory for NIFTI files", required=True)
parser.add_argument("--workdir", help="working directory for temporary files", required=False,default="/tmp")
parser.add_argument("--overwrite", help="Overwrite NIFTI files if they exist")
parser.add_argument("--upload-by-ref", help="Upload \"by reference\". Only use if your host can read your file system.")
parser.add_argument("--cleanup", help="Attempt to clean up temporary files")
parser.add_argument("--debugmode", help="Attempt to clean up temporary files")
parser.add_argument("--workflowId", help="Pipeline workflow ID")
parser.add_argument('--version', action='version', version='%(prog)s 1')

args, unknown_args = parser.parse_known_args()
host = cleanServer(args.host)
proc_steps = args.proc_steps
if proc_steps is None:
    proc_steps = ''
if not proc_steps:
    proc_steps = 'mriqcgroup:,eddyqcgroup:'
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


builddir = os.getcwd()

# Set up working directory
if not os.access(dicomdir, os.R_OK):
    os.mkdir(dicomdir)
if not os.access(niftidir, os.R_OK):
    os.mkdir(niftidir)
bidsdir = niftidir + "/BIDS"
if not os.access(bidsdir, os.R_OK):
    os.mkdir(bidsdir)


BIDS_RESOURCE_FOLDER='BIDS-AACAZ'
LOG_RESOURCE_FOLDER='LOGS-AACAZ'
CONFIG_RESOURCE_FOLDER='CONFIG-AACAZ'
EDDYQC_RESOURCE_FOLDER='EDDYQC-AACAZ'
MRIQC_RESOURCE_FOLDER='MRIQC-AACAZ'
FMRIPREP_RESOURCE_FOLDER='FMRIPREP-AACAZ'
QSIPREP_RESOURCE_FOLDER='QSIPREP-AACAZ'
PHANTOMROI_RESOURCE_FOLDER='PHANTOMROI-AACAZ'
PHANTOMQC_RESOURCE_FOLDER='PHANTOMQC-AACAZ'

EDDYQC_PROJECT_RESOURCE_FOLDER='EDDYQC-AACAZ-GROUP'
MRIQC_PROJECT_RESOURCE_FOLDER='MRIQC-AACAZ-GROUP'
PHANTOMQC_PROJECT_RESOURCE_FOLDER='PHANTOMQC-AACAZ-GROUP'

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
sess = requests.Session()
sess.verify = False
sess.auth = (args.user, args.password)

FSLICENSE=os.path.join('/src','license.txt')


# massive try block to fail gracefully
try:
    MAXRECS=10
    CURRSTEP='initialisation'
    if CURRSTEP in proc_steps:  
        os.chdir("/tmp")

        # find step-specific parameters
        step_info=''
        proc_steps_list=proc_steps.split(",")
        for step_item in proc_steps_list:
            if CURRSTEP in step_item:
                step_info = step_item
                break

        # number of records to display in phantom report
        SUBSTEP=':maxrecs'
        SUBSTEPOUT=SUBSTEP + '='
        if SUBSTEP in step_info:
            if SUBSTEPOUT in step_info:
                if step_info.split(SUBSTEPOUT)[1]:
                    maxrecstring = step_info.split(SUBSTEPOUT)[1].split(':')[0].strip()
                    if maxrecstring.isnumeric():
                        MAXRECS=int(maxrecstring)
                        logtext (LOGFILE,'initialisation:maxrecs display %s records in phantom report.' % (str(MAXRECS)))
                    else:
                        logtext (LOGFILE,'initialisation:maxrecs display is non numeric %s. Returning all records' % (maxrecstring))
                        MAXRECS = None

                else:
                    logtext (LOGFILE,'initialisation:maxrecs parameter missing optional location information. Using default value %s.' % (str(MAXRECS)))


    # group eddy qc
    if 'eddyqcgroup' in proc_steps:
        os.chdir("/tmp")

        # find step-specific parameters
        step_info=''
        proc_steps_list=proc_steps.split(",")
        for step_item in proc_steps_list:
            if 'eddyqcgroup:' in step_item:
                step_info = step_item
                break

        EDDYQCGROUPFOLDER=os.path.join(niftidir,EDDYQC_PROJECT_RESOURCE_FOLDER)
        if not os.access(EDDYQCGROUPFOLDER, os.R_OK):
            os.mkdir(EDDYQCGROUPFOLDER)

        resourceExists = checkProjectResource(EDDYQC_PROJECT_RESOURCE_FOLDER, project, host,sess)
        if not resourceExists or overwrite:

            eddyquaddir=os.path.join(EDDYQCGROUPFOLDER,'quad')
            if not os.path.isdir(eddyquaddir):
                os.mkdir(eddyquaddir)
            eddygroupdir=os.path.join(EDDYQCGROUPFOLDER,'squad')
            if os.path.exists(eddygroupdir):
                rmtree(eddygroupdir)

            filesDownloaded = downloadAllSessionfilesFiltered(EDDYQC_RESOURCE_FOLDER, project, eddyquaddir,True, host, sess, False, None, False, None, True, 'quad')
            
            quadfolders=os.path.join(eddyquaddir,'quad_folders.txt')

            eddyQuadDirs=''
            eddyQuadDirs='\n'.join([os.path.join(eddyquaddir, os.path.dirname(s)) for s in filesDownloaded if 'qc.json' in s])
            f=open(quadfolders, 'w+')
            f.write (eddyQuadDirs)
            f.close()
        
            message = 'Following directories will be used for SQUAD:\n%s' % eddyQuadDirs
            logtext (LOGFILE, message)
        
            eddysquad_command = "eddy_squad {} -o {}".format(quadfolders, eddygroupdir).split() 
            logtext(LOGFILE, ' '.join(eddysquad_command))
            logtext(LOGFILE, str(subprocess.check_output(eddysquad_command)))

            # Uploading EDDYQC files
            if resourceExists and overwrite:
                logtext(LOGFILE, 'Deleting existing %s folder for project %s' % (EDDYQC_PROJECT_RESOURCE_FOLDER, project))
                deleteFolder(workflowId, "/data/projects/%s/resources/%s" % (project,EDDYQC_PROJECT_RESOURCE_FOLDER) , LOGFILE, host,sess)

                
            # Uploading Group EDDYQC files
            print ('Uploading EDDYQC files for project %s.' % project)
            uploadfiles (workflowId , "EDDYQC_NIFTI", "EDDYQC_FILES" ,"EDDYQC", eddygroupdir,  "/data/projects/%s/resources/%s/files" % (project,EDDYQC_PROJECT_RESOURCE_FOLDER) ,host,sess,uploadByRef,args)

        else:
            message = 'Looks like EDDYQC has already been run for project %s. If you want to rerun then set overwrite flag to True.' % project
            print (message)
            logtext (LOGFILE, message)

    # run group MRIQC
    if 'mriqcgroup' in proc_steps:
        os.chdir("/tmp")

        # find step-specific parameters
        step_info=''
        proc_steps_list=proc_steps.split(",")
        for step_item in proc_steps_list:
            if 'mriqcgroup:' in step_item:
                step_info = step_item
                break

        mriqc_params=""
    

        MRIQCGROUPFOLDER=os.path.join(niftidir,MRIQC_PROJECT_RESOURCE_FOLDER)
        if not os.access(MRIQCGROUPFOLDER, os.R_OK):
            os.mkdir(MRIQCGROUPFOLDER)

        resourceExists = checkProjectResource(MRIQC_PROJECT_RESOURCE_FOLDER, project, host,sess)
        if not resourceExists or overwrite:
    
            mriqcOutdir=os.path.join(MRIQCGROUPFOLDER,'MRIQC')
            if not os.path.isdir(mriqcOutdir):
                 os.mkdir(mriqcOutdir)
    
            projectBidsDir=os.path.join(MRIQCGROUPFOLDER,project)
            if not os.path.isdir(projectBidsDir):
                os.mkdir(projectBidsDir)

            bidsfilesDownloaded = getBids(project, projectBidsDir, BIDS_RESOURCE_FOLDER, host, sess)
            mriqcfilesDownloaded = downloadAllSessionfiles (MRIQC_RESOURCE_FOLDER, project, mriqcOutdir, True,host,sess,False)
            mriqc_command = "mriqc {} {} group {}".format(projectBidsDir, mriqcOutdir, mriqc_params).split() 
            logtext(LOGFILE, subprocess.check_output(mriqc_command))

            # Uploading EDDYQC files
            if resourceExists and overwrite:
                logtext(LOGFILE, 'Deleting existing %s folder for project %s' % (MRIQC_PROJECT_RESOURCE_FOLDER, project))
                deleteFolder(workflowId, "/data/projects/%s/resources/%s" % (project,MRIQC_PROJECT_RESOURCE_FOLDER) , LOGFILE, host,sess)

            # Uploading MRIQC files
            logtext(LOGFILE,'Uploading group MRIQC files for project %s' % project)
            uploadfiles (workflowId , "MRIQC_NIFTI", "MRIQC_FILES" ,"MRIQC",mriqcOutdir, "/data/projects/%s/resources/%s/files" % (project, MRIQC_PROJECT_RESOURCE_FOLDER),host,sess,uploadByRef,args )
        else:
            message = 'Looks like MRIQC has already been run for project %s. If you want to rerun then set overwrite flag to True.' % project
            print (message)
            logtext (LOGFILE, message)

    if 'phantomqcgroup' in proc_steps: 

        os.chdir("/tmp")

        # find step-specific parameters
        step_info=''
        proc_steps_list=proc_steps.split(",")
        for step_item in proc_steps_list:
            if 'phantomqc:' in step_item:
                step_info = step_item
                break

        PHANTOMQCGROUPFOLDER=os.path.join(niftidir,PHANTOMQC_PROJECT_RESOURCE_FOLDER)
        if not os.access(PHANTOMQCGROUPFOLDER, os.R_OK):
            os.mkdir(PHANTOMQCGROUPFOLDER)

        resourceExists = checkProjectResource(PHANTOMQC_PROJECT_RESOURCE_FOLDER, project, host,sess)
        if not resourceExists or overwrite:

            output_dir=os.path.join(PHANTOMQCGROUPFOLDER,'outputdir')
            if not os.path.isdir( output_dir):
                os.mkdir(output_dir)

            report_dir=os.path.join(PHANTOMQCGROUPFOLDER,'reportdir')
            if not os.path.isdir( report_dir):
                os.mkdir(report_dir)

            report_json_dir=os.path.join(PHANTOMQCGROUPFOLDER,'jsons')
            if not os.path.isdir( report_json_dir):
                os.mkdir(report_json_dir)

            report_image_dir=os.path.join(report_dir,'images')
            if not os.path.isdir( report_image_dir):
                os.mkdir(report_image_dir)

            filesDownloaded = downloadAllSessionfilesFiltered (PHANTOMQC_RESOURCE_FOLDER, project, report_json_dir, True, host,sess,bump=True,target="finalreport.json",exactmatch=False, refdate=None, retainFolderTree=False)

            reportjson = [os.path.join(report_json_dir, s) for s in filesDownloaded if 'finalreport.json' in s]

            if len(reportjson) > 0:

                reportdict = getSortedReportSet(reportjson, MAXRECS)

                fullgroupjson=os.path.join(output_dir, "{}_phantom_groupfinalreport.json".format(project))
                createGroupJson(reportdict, fullgroupjson)

                style_source = "/src/style.css"
                style_dest = os.path.join(report_dir,'style.css')
                fileCopy(style_source,style_dest)

                CURRENTDIR=os.getcwd()
                os.chdir(report_dir)

                doc = createPhantomGroupQCReport('./style.css', './images', reportdict)

                final_report_html = os.path.join(report_dir, "{}_phantom_groupfinalreport.html".format(project))
                final_report_inline_html = os.path.join(output_dir, "{}_phantom_groupfinalreport_inline.html".format(project))
                with open(final_report_html, 'w') as file:
                    file.write(doc.render())
                make_html_images_inline(final_report_html, final_report_inline_html)

                os.chdir(CURRENTDIR)

                copytree(report_dir, os.path.join(output_dir, 'htmlreport'))

                # Uploading PHANTOMQC files
                if resourceExists and overwrite:
                    logtext(LOGFILE, 'Deleting existing %s folder for project %s' % (PHANTOMQC_PROJECT_RESOURCE_FOLDER, project))
                    deleteFolder(workflowId, "/data/projects/%s/resources/%s" % (project,PHANTOMQC_PROJECT_RESOURCE_FOLDER) , LOGFILE, host,sess)

                logtext(LOGFILE,'Uploading group PHANTOMQC files for project %s' % project)
                uploadfiles (workflowId , "PHANTOMQC_NIFTI", "PHANTOMQC_FILES" ,"PHANTOMQC",output_dir, "/data/projects/%s/resources/%s/files" % (project, PHANTOMQC_PROJECT_RESOURCE_FOLDER),host,sess,uploadByRef,args )
                if cleanup and checkProjectResource(PHANTOMQC_PROJECT_RESOURCE_FOLDER, project, host,sess):
                    logtext (LOGFILE, 'Cleaning up %s directory.' % PHANTOMQCGROUPFOLDER)
                    rmtree(PHANTOMQCGROUPFOLDER)
            else:
                logtext(LOGFILE,'{} Json reports not found for any sessions in  {}'.format(PHANTOMQC_RESOURCE_FOLDER, project))

        else:
            message = 'Looks like PHANTOMQC has already been run for project %s. If you want to rerun then set overwrite flag to True.' % project
            print (message)
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
                                deleteFolder("/data/experiments/%s/resources/%s" % (session,INPUT_FOLDER), LOGFILE,sess)                    
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
            deleteFolder("/data/experiments/%s/resources/%s" % (session,LOG_RESOURCE_FOLDER), LOGFILE ,sess)
            uploadfiles (workflowId , "LOG_TXT", "LOG_FILES" ,"LOG", LOGFOLDER, "/data/experiments/%s/resources/%s/files" % (session,LOG_RESOURCE_FOLDER) ,host,sess,uploadByRef,args)
        except Exception as e:
            logtext (LOGFILE, 'Exception thrown in Finally Block.')
            logtext (LOGFILE, str(e))
    LOGFILE.close()
