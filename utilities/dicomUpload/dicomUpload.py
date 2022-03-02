# dicomUpload
from __future__ import print_function, division, absolute_import, unicode_literals
import os
import glob
import datetime
import json
import multiprocessing as mp
import getpass


__version__=0.1

def upload_dicoms(uploadparams):

    zipmode=uploadparams.split("^^")[0]
    user=uploadparams.split("^^")[1]
    password=uploadparams.split("^^")[2]
    url=uploadparams.split("^^")[3]
    project=uploadparams.split("^^")[4]
    subid=uploadparams.split("^^")[5]
    sessionid=uploadparams.split("^^")[6]
    zipfile=uploadparams.split("^^")[7]
    sessiondir=uploadparams.split("^^")[8]
    skipdir=uploadparams.split("^^")[9]


    skipadd=''
    if len(skipdir)>0:
        skipadd='-x {}'.format(skipdir)

    sesname=subid+"_"+sessionid

    if zipmode != "asis":
        rm_command = 'rm -f {}'.format(zipfile)
        os.system(rm_command)

        zip_command = 'zip -r -q {} {} {}'.format(zipfile, sessiondir, skipadd)
        os.system(zip_command)

    curl_command = 'curl -k -u {}:{} -X POST "{}/data/services/import?PROJECT_ID={}&SUBJECT_ID={}&EXPT_LABEL={}&import-handler=DICOM-zip&overwrite=append" -F "file=@{}"'.format(user,password,url,project,subid,sesname,zipfile)
    os.system(curl_command)

def isTrue(arg):
    return arg is not None and (arg == 'Y' or arg == '1' or arg == 'True')

def get_parser():
    from argparse import ArgumentParser
    from argparse import RawTextHelpFormatter

    parser = ArgumentParser(description="Python DICOM upload for XNAT."
        "Multiprocessing bulk upload.",formatter_class=RawTextHelpFormatter)
    parser.add_argument('xnaturl', action='store',  
        help='url path to xnat e.g. https://xnat.org.')
    parser.add_argument('project', action='store',
        help='Project ID')
    parser.add_argument('dicomdir', action='store', 
        help='The root directory that contains the dicom folder of dicoms to send.')
    parser.add_argument('--config', action='store',
        help='File containing  config info for managing dicoms.')
    parser.add_argument('--logname', action='store',
        help='name for the log file (without extension) which will be created in work directory.')
    parser.add_argument('--workdir', action='store',
        help='Work directory for output of log file and other temporary files')
    parser.add_argument('--procs', action='store',
        help='Number of multiprocessing cores')
    parser.add_argument('--zipmode', action='store',
        help='How to handle dicoms if provided as zipped file.["nozip"] ignore zips files in folder and assume that uncompressed \
        dicoms provided. ["asis"] assumes that single zipfile provided for each session and upload as is. ["process"] unzip and \
        perform exclusion step and then rezip for full upload. This last option will be the most computationally demanding', default="nozip")
    parser.add_argument('--debugmode', action='store',
        help='Run in debug mode as multi-threaded app. Some issues still ot resolve with this.')


    return parser

def logtext(logfile, textstr):
    stamp=datetime.datetime.now().strftime("%m-%d-%y %H:%M:%S%p")
    textstring=stamp + '  ' + textstr
    print(textstring)
    if not logfile == None:
        logfile.write(textstring+'\n')


def main():
    opts = get_parser().parse_args()
    ROOTDIR=os.path.abspath(opts.dicomdir)
    user=input("User: ")
    password = getpass.getpass()
    xnaturl=opts.xnaturl
    project=opts.project
    debugmode = isTrue(opts.debugmode)
    zipmode = opts.zipmode

    if opts.workdir:
        WORKDIR=os.path.abspath(opts.workdir)
    else:
        WORKDIR=os.path.join(os.getcwd(),"work")

    if not os.path.isdir(WORKDIR):
        os.mkdir(WORKDIR)

    if opts.config:
        CONFIGFILE=os.path.abspath(opts.config)
    else:
        CONFIGFILE=None

    exclusions=[]
    if not CONFIGFILE == None:
        configFile=open(CONFIGFILE)
        configs=json.load(configFile)
        configFile.close()
        exclusions=configs["Exclude"]

    if opts.logname:
        BASELOGNAME=opts.logname
    else:
        BASELOGNAME='dicomUpload'

    TIMESTAMP=datetime.datetime.now().strftime("%m%d%y%H%M%S%p")
    LOGFILENAME=BASELOGNAME + '_' + TIMESTAMP + '.log'
    LOGFILE = open(os.path.join(WORKDIR,LOGFILENAME), 'w')

    #start pool
    if not opts.procs:
        procs=mp.cpu_count()
    else:
        procs=opt.procs

    if debugmode:
        pool = mp.Pool(procs)


    # enter password and userid
    #logtext(LOGFILE,"Please enter lgin credentials for '" + xnaturl)
    #user=input('userid :')
    #password=getpass.getpass(prompt='password : ', stream=None)

    subjects = [f for f in glob.glob(ROOTDIR + '/*') if os.path.isdir(f)]

    dicombatch=[]
    for subject in subjects:
        subid=os.path.basename(subject)
        logtext(LOGFILE,"processing subject '" + subid + "' located at " + subject)
        #ae.add_requested_context(MRImageStorage)

        sessions = [s for s in os.listdir(subject) if os.path.isdir(os.path.join(subject,s))]
        
        for session in sessions:
            skipdir=''
            fulldicomdir=subject + "/" + session
            zipfile = os.path.join(WORKDIR,subid+"_"+session+".zip")
            SKIP_PROCESSING=False

            #  if ignoring zip files then traverse the hierarchy and find and add zip files to skipadd
            if zipmode == "nozip":
                for root, dirs, files in os.walk(fulldicomdir):
                    for file in files:
                        if file.endswith(".zip"):
                            skipdir=skipdir + '"{}" '.format(os.path.join(root,file))
            else:
                # if single zip files not found then flag an error
                ziplist=[]
                for root, dirs, files in os.walk(fulldicomdir):
                    for file in files:
                        if file.endswith(".zip"):
                            ziplist.append(os.path.join(root,file))
                if not len(ziplist) == 1:
                    logtext(LOGFILE, "Require 1 zip file for each subject/session. Found {} zipfiles for {}/{}.".format(str(len(ziplist)), subid, session))
                    SKIP_PROCESSING=True

            if zipmode == "process" and not SKIP_PROCESSING:
                orig_zipfile=ziplist[0]
                # extract t working directiory
                worksubdir=os.path.join(WORKDIR,subid)
                if not os.path.isdir(worksubdir):
                    os.mkdir(worksubdir)
                worksesdir=os.path.join(worksubdir,session)
                if not os.path.isdir(worksesdir):
                    os.mkdir(worksesdir)
                unzip_command = 'unzip -q -o {} -d {}'.format(orig_zipfile, worksesdir)
                os.system(unzip_command)
                fulldicomdir=worksesdir

            if zipmode == "asis" and not SKIP_PROCESSING:
                zipfile=ziplist[0]
                logtext(LOGFILE,"zip file {} for {}/{} will be uploaded.".format(zipfile, subid,session))

            if len(exclusions) > 0 and zipmode != "asis" and not SKIP_PROCESSING:
                logtext(LOGFILE, "Processing Exclusions for Session: " + session)
                for root, dirs, files in os.walk(fulldicomdir):
                    for subdir in dirs:
                        for index, value in enumerate(exclusions):
                            if value.upper() in subdir.upper():
                                 logtext(LOGFILE, subdir + " in " + root + " will be excluded.")
                                 skipdir=skipdir + '"{}/*" '.format(os.path.join(root,subdir))
                                 continue                


            if not SKIP_PROCESSING: 
                mpcommand='{}^^{}^^{}^^{}^^{}^^{}^^{}^^{}^^{}^^{}'.format(zipmode, user,password,xnaturl,project,subid,session,zipfile, fulldicomdir,skipdir)
                dicombatch.append(mpcommand)

    if not debugmode:
        sessioncount=1
        logtext(LOGFILE,"beginning upload of {} subject/sessions Batches".format(str(len(dicombatch))))
        for dicomcmd in dicombatch:
            sub_label=dicomcmd.split("^^")[5]
            ses_label=sub_label+'_' + dicomcmd.split("^^")[6]
            zip_label=dicomcmd.split("^^")[7]
            logtext(LOGFILE, "Batch {}:  Processing Subject_Label:{}  Session_Label:{}  Zip_File:{} ".format(str(sessioncount), sub_label,ses_label,zip_label))
            upload_dicoms(dicomcmd)
            sessioncount=sessioncount + 1

    else:
        pool.map(upload_dicoms,(dicombatch))

    if debugmode:
        pool.close()
        pool.join()

    logtext(LOGFILE,"upload complete")
    LOGFILE.close()
# This is the standard boilerplate that calls the main() function.
if __name__ == '__main__':
    main()
