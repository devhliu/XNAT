#!/usr/bin/env python
# dicomUpload
from __future__ import print_function, division, absolute_import, unicode_literals
import os
import glob
import datetime
import json
import multiprocessing as mp


__version__=0.1

def upload_dicoms(uploadparams):
    
    user=uploadparams.split("^^")[0]
    password=uploadparams.split("^^")[1]
    url=uploadparams.split("^^")[2]
    project=uploadparams.split("^^")[3]
    subid=uploadparams.split("^^")[4]
    sessionid=uploadparams.split("^^")[5]
    zipfile=uploadparams.split("^^")[6]
    sessiondir=uploadparams.split("^^")[7]
    skipdir=uploadparams.split("^^")[8]


    skipadd=''
    if len(skipdir)>0:
        skipadd='-x {}'.format(skipdir)

    sesname=subid+"_"+sessionid

    logtext(None, "Processing Subject:{} Session:{} sessiondir:{} ".format(subid,sesname,sessiondir))

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
    parser.add_argument('user', action='store',
        help='User id for logon to xnat')
    parser.add_argument('password', action='store',
        help='password for login')
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
    parser.add_argument('--debugmode', action='store',
        help='Run in debug mode as single thread')


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
    password=opts.password
    user=opts.user
    xnaturl=opts.xnaturl
    project=opts.project
    debugmode = isTrue(opts.debugmode)

    if opts.workdir:
        WORKDIR=os.path.abspath(opts.workdir)
    else:
        WORKDIR=os.getcwd()

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
        
        for session in os.listdir(subject):
            skipdir=''
            logtext(LOGFILE, "Processing Session: " + session)
            fulldicomdir=subject + "/" + session
            # incorporate skipping dicoms at a later date?
            for dicomdir in os.listdir(subject + '/' + session):
                logtext(LOGFILE, "Processing Dicom: " + dicomdir)
                skipdicom=False

                for index, value in enumerate(exclusions):
                    if value.upper() in dicomdir.upper():
                        logtext(LOGFILE, dicomdir + " will be excluded. continuing to next dicom")
                        skipdicom=True
                        break

                if skipdicom:
                    skipdir=skipdir + '"{}/*" '.format(fulldicomdir + '/' + dicomdir)
                    continue

            #    fulldicomdir=subject + "/" + session + "/" + dicomdir
             
            zipfile = os.path.join(WORKDIR,subid+"_"+session+".zip")
            mpcommand='{}^^{}^^{}^^{}^^{}^^{}^^{}^^{}^^{}'.format(user,password,xnaturl,project,subid,session,zipfile, fulldicomdir,skipdir)
            dicombatch.append(mpcommand)

    if not debugmode:
        for dicomcmd in dicombatch:
            upload_dicoms(dicomcmd)

    else:
        pool.map(upload_dicoms,(dicombatch))

    if debugmode:
        pool.close()
        pool.join()

    logtext(LOGFILE,"upload complete")
# This is the standard boilerplate that calls the main() function.
if __name__ == '__main__':
    main()
