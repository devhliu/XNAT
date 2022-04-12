# guiDicomUpload
import os
import sys
import glob
import datetime
import json
import getpass
import requests
import zipfile as zp
from tkinter import *
from tkinter import filedialog

##############################
# Very basic implementation that uses standard pythin libraries
# To DO:
#    1. ensure code flow is optimal and efficient
#    2. Use pydicom library for exclusions (checking Protocol or Series Description)
#    3. Use pydicom to identify sessions (so only need to point to root directory) -emulating XNAT-Desktop-Client
#    4. Improve GUI controls 
#    5. Intelligence - validate entries, enable/disable buttons depending on values in fields
#
#############################

__version__=0.1


def get_all_file_paths(directory, skipdir):
    file_paths=[]
    for root, directories,files in os.walk(directory):
        for filename in files:
            filepath = os.path.join(root,filename)
            file_paths.append(filepath)

    for exclude in skipdir:
        file_paths=[x for x in file_paths if exclude not in x]

    return file_paths


def upload_dicoms(uploadparams, skipdir):

    zipmode=uploadparams.split("^^")[0]
    user=uploadparams.split("^^")[1]
    password=uploadparams.split("^^")[2]
    url=uploadparams.split("^^")[3]
    project=uploadparams.split("^^")[4]
    subid=uploadparams.split("^^")[5]
    sessionid=uploadparams.split("^^")[6]
    zipfile=uploadparams.split("^^")[7]
    sessiondir=uploadparams.split("^^")[8]
      

    sesname=subid+"_"+sessionid

    if zipmode != "asis":
        # Remove zipfile if it exists
        if os.path.exists(zipfile):
            os.remove(zipfile)

        file_paths=get_all_file_paths(sessiondir, skipdir)

        with zp.ZipFile(zipfile,'w') as zip:
            for file in file_paths:
                zip.write(file)

    params = {
       'PROJECT_ID': project,
       'SUBJECT_ID': subid,
       'EXPT_LABEL': sesname,
       'import-handler': 'DICOM-zip',
       'overwrite': 'append',
    }

    files = {
        'file': (zipfile, open(zipfile, 'rb')),
    }

    response = requests.post('{}/data/services/import'.format(url), params=params, files=files, auth=(user, password))

def isTrue(arg):
    return arg is not None and (arg == 'Y' or arg == '1' or arg == 'True')

def get_gui_parser():
    from argparse import ArgumentParser
    parser = ArgumentParser(description="Python gui parser")
    return parser

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

def maingui():
    guiopts=get_gui_parser()
    guiopts.dicomdir = None 
    guiopts.user = None
    guiopts.password = None
    guiopts.xnaturl = None
    guiopts.project = None
    guiopts.debugmode = None
    guiopts.zipmode = None
    guiopts.workdir = None
    guiopts.config = None
    guiopts.logname = None

    # load defaults if available
    uploadConfigFile=os.path.join(os.getcwd(),'PAN-XNAT-config.json')
 
    xnaturldef=''
    userdef=''
    projectdef=''
    if os.path.exists(uploadConfigFile):
        with open(uploadConfigFile,'r') as outfile:
            savejson=json.load(outfile)

        try:     
            xnaturldef=savejson["url"]
            userdef=savejson["user"]
            projectdef=savejson["project"]
        except KeyError:
            logtext(LOGFILE,str(KeyError))
            logtext(LOGFILE,"Some fields not available in config file {}.".format(uploadConfigFile))


    def set_directory(guientry):
        folder_selected=filedialog.askdirectory()
        guientry.delete(0,END)
        guientry.insert(0,folder_selected)

    def set_file(guientry):
        file_selected=filedialog.askopenfilename()
        guientry.delete(0,END)
        guientry.insert(0,file_selected)

    root = Tk()
    root.title('PAN XNAT dicomUpload gui')
    frame0 = LabelFrame(root,padx=5,pady=5)
    frame0.grid(row=0,column=0,sticky=E+W)
    frame1 = LabelFrame(root, text='Folder Setup',padx=5,pady=5)
    frame1.grid(row=1,column=0,sticky=N+S)
    frame2 = LabelFrame(root, text='PAN XNAT Credentials',padx=5,pady=5)
    frame2.grid(row=1,column=1,sticky=N+S)
    frame3 = LabelFrame(root, text='Choose Zip Mode',padx=5,pady=5)
    frame3.grid(row=2,column=0,sticky=N+S+E+W)
    frame4 = LabelFrame(root, text='Command',padx=5,pady=5)
    frame4.grid(row=2,column=1,sticky=N+S+E+W)

    # set up frame0
    title_lbl  = Label(frame0, text = "PAN XNAT Dicom Uploader", font=("Arial",20))
    title_lbl.grid(row=0,column=0)

    #set up frame1
    dicomroot_lbl = Label(frame1, text="Dicom Root Directory:",padx=5,pady=5)
    dicomroot_ent = Entry(frame1, width=30)
    dicomroot_but = Button(frame1, text='Browse for Dicom directory',command=lambda: set_directory(dicomroot_ent))
    dicomroot_lbl.grid(row=0,column=0)
    dicomroot_ent.grid(row=0,column=1)
    dicomroot_but.grid(row=0,column=2)

    exclusion_lbl = Label(frame1, text="Exclusions File:",padx=5,pady=5)
    exclusion_ent = Entry(frame1, width=30)
    exclusion_but = Button(frame1, text='Browse for Exclusion File',command=lambda: set_file(exclusion_ent))
    exclusion_lbl.grid(row=1,column=0)
    exclusion_ent.grid(row=1,column=1)
    exclusion_but.grid(row=1,column=2)

    ziprow=0
    zipmode = StringVar()
    ziptypes=(('Dicoms are in raw format','nozip'),('Dicoms are compressed. Upload with exclusions if available.','process'),('Dicoms are compressed. Exclusions ignored','asis'))
    for ziptype in ziptypes:
        ziprow=ziprow+1
        r = Radiobutton(frame3, text=ziptype[0], value=ziptype[1],variable=zipmode,anchor=W)
        r.grid(row=ziprow,column=0)
 
    zipmode.set("nozip")
    # set up frame2      

    url_lbl = Label(frame2, text="PAN XNAT URL:",padx=5,pady=5)
    url_ent = Entry(frame2, width=30)
    url_lbl.grid(row=0,column=0)
    url_ent.grid(row=0,column=1)
    url_ent.insert(0,xnaturldef)

    proj_lbl = Label(frame2, text="Project:",padx=5,pady=5)
    proj_ent = Entry(frame2, width=30)
    proj_lbl.grid(row=1,column=0)
    proj_ent.grid(row=1,column=1)
    proj_ent.insert(0,projectdef)

    user_lbl = Label(frame2, text="User:",padx=5,pady=5)
    user_ent = Entry(frame2, width=30)
    user_lbl.grid(row=2,column=0)
    user_ent.grid(row=2,column=1)
    user_ent.insert(0,userdef)

    pass_lbl = Label(frame2, text="Password:",padx=5,pady=5)
    pass_ent = Entry(frame2, show="*", width=30)
    pass_lbl.grid(row=3,column=0)
    pass_ent.grid(row=3,column=1)

    def runapp(guiopts):
        guiopts.dicomdir = dicomroot_ent.get() 
        guiopts.user = user_ent.get()
        guiopts.password = pass_ent.get()
        guiopts.xnaturl = url_ent.get()
        guiopts.project = proj_ent.get()
        guiopts.debugmode = False
        guiopts.zipmode = zipmode.get()
        guiopts.workdir = None
        guiopts.config = exclusion_ent.get()
        guiopts.logname = None
        print("python /guiDicomUpload.py {} {} {} --user {} --password ***** --config {} --zipmode {}".format(guiopts.xnaturl, guiopts.project, guiopts.dicomdir, guiopts.user,guiopts.config,guiopts.zipmode  ))
        main(guiopts)
    
    frame4.grid_columnconfigure(1,weight=1)
    run_but = Button(frame4, text='Do Upload >>',command=lambda: runapp(guiopts))
    run_but.grid(row=0,column=0)
    close_but = Button(frame4, text='exit',command=root.destroy)
    close_but.grid(row=0,column=1,  sticky=E)


    #main(guiopts)
    root.mainloop()


def maincommand():
    opts = get_parser().parse_args()
    main(opts)

def main(opts):
    ROOTDIR=os.path.abspath(opts.dicomdir)
    if not opts.user:
        user=input("User: ")
    else:
        user=opts.user
    if not opts.password:
        password = getpass.getpass()
    else:
        password = opts.password
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
        if not os.path.exists(CONFIGFILE):
            CONFIGFILE=None
    else:
        CONFIGFILE=None

    if opts.logname:
        BASELOGNAME=opts.logname
    else:
        BASELOGNAME='dicomUpload'

    exclusions=[]
    if not CONFIGFILE == None:
        configFile=open(CONFIGFILE)
        configs=json.load(configFile)
        configFile.close()
        exclusions=configs["Exclude"]


    TIMESTAMP=datetime.datetime.now().strftime("%m%d%y%H%M%S%p")
    LOGFILENAME=BASELOGNAME + '_' + TIMESTAMP + '.log'
    LOGFILE = open(os.path.join(WORKDIR,LOGFILENAME), 'w')


    subjects = [f for f in glob.glob(ROOTDIR + '/*') if os.path.isdir(f)]

    dicombatch=[]
    for subject in subjects:
        subid=os.path.basename(subject)
        logtext(LOGFILE,"processing subject '" + subid + "' located at " + subject)
        #ae.add_requested_context(MRImageStorage)

        sessions = [s for s in os.listdir(subject) if os.path.isdir(os.path.join(subject,s))]
        
        for session in sessions:
            skipdir=[]
            fulldicomdir=subject + "/" + session
            zipfile = os.path.join(WORKDIR,subid+"_"+session+".zip")
            SKIP_PROCESSING=False
            ziplist=[]

            #  if ignoring zip files then traverse the hierarchy and find and add zip files to skipadd
            if zipmode == "nozip":
                for root, dirs, files in os.walk(fulldicomdir):
                    for file in files:
                        if file.endswith(".zip"):
                            skipdir.append('{}'.format(os.path.join(root,file)))
            else:
                # if single zip files not found then flag an error
                
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

                CURRDIR=os.getcwd()
                os.chdir(worksesdir)
                with zp.ZipFile(orig_zipfile,'r') as zip:
                    zip.extractall()

                fulldicomdir=worksesdir
                os.chdir(CURRDIR)

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
                                 skipdir.append('{}/'.format(os.path.join(root,subdir)))
                                 continue



            if not SKIP_PROCESSING: 
                mpcommand='{}^^{}^^{}^^{}^^{}^^{}^^{}^^{}^^{}'.format(zipmode, user,password,xnaturl,project,subid,session,zipfile, fulldicomdir)
                dicombatch.append([mpcommand, skipdir])

    sessioncount=1
    logtext(LOGFILE,"beginning upload of {} subject/sessions Batches".format(str(len(dicombatch))))
    for dicomcmd in dicombatch:
        sub_label=dicomcmd[0].split("^^")[5]
        ses_label=sub_label+'_' + dicomcmd[0].split("^^")[6]
        zip_label=dicomcmd[0].split("^^")[7]
        logtext(LOGFILE, "Batch {}:  Processing Subject_Label:{}  Session_Label:{}  Zip_File:{} ".format(str(sessioncount), sub_label,ses_label,zip_label))
        upload_dicoms(dicomcmd[0],dicomcmd[1])
        sessioncount=sessioncount + 1

    logtext(LOGFILE, "Saving defaults to uploadConfig.json")
    uploadConfigFile=os.path.join(os.getcwd(),'PAN-XNAT-config.json')
    savejson={}
    savejson["url"]=xnaturl
    savejson["user"]=user
    savejson["project"]=project
    with open(uploadConfigFile,'w') as outfile:
        json.dump(savejson, outfile, indent=2)

    logtext(LOGFILE,"upload complete")
    LOGFILE.close()
# This is the standard boilerplate that calls the main() function.
if __name__ == '__main__':
    if sys.argv[1].upper() == 'GUI':
        maingui()
    else:
        maincommand()
