from xnatutils.genutils import *
import os
import getpass
__version__=0.1

def get_parser():
    from argparse import ArgumentParser
    from argparse import RawTextHelpFormatter
    parser = ArgumentParser(description="upload resource sto XNAT")
    parser.add_argument("command", default="downloadSession", help="downloadSession, downloadAllSessions, downloadSubject. downloadSubjectSessions, downloadProject, downloadSessionDicomZip")
    parser.add_argument("xnatfolder", default="DEFAULT-ORBISYS", help="collection name")
    parser.add_argument("outputdir", default="./", help="output directory")
    parser.add_argument("--host", default="https://cnda.wustl.edu", help="CNDA host", required=True)
    parser.add_argument("--separate", default="N",help="store sessions in sepparate folders",required=False)
    parser.add_argument("--session", help="Session ID", required=False)
    parser.add_argument("--subject", help="subjecy ID", required=False)
    parser.add_argument("--project", help="Project", required=False)
    parser.add_argument("--user", help="user", required=False)
    parser.add_argument("--password", help="password", required=False)    
    parser.add_argument('--version', action='version', version='%(prog)s 1')
    return parser

def main():
    args, unknown_args = get_parser().parse_known_args()
    host = cleanServer(args.host)
    
    command = args.command
    xnatfolder = args.xnatfolder
    if args.outputdir is None:
        outputdir=os.path.join(os.getcwd(),'output')
    else:
        outputdir=os.path.abspath(args.outputdir)

    if not os.access(outputdir, os.R_OK):
        os.mkdir(outputdir)

    if args.user is None:
        user = input("User: ")
        args.user = user

    if args.password is None:
        password = getpass.getpass()
        args.password = password
    
    session = args.session
    subject = args.subject
    project = args.project

    separate = isTrue(args.separate)

    additionalArgs = unknown_args if unknown_args is not None else []

    # Set up session
    connection = startSession(user,password)

   
    if command == 'downloadSession':
        if session is None:
            print("Cannot download session without a valid session label. Please specify session with --session")
        else:
            filedown = downloadSessionfiles (xnatfolder, session, outputdir, True,host, connection)
     
    elif command == 'downloadAllSessions':
        if project is None:
            print("Cannot download all sessions without a valid project label. Please specify project with --project")
        else:
            filedown = downloadAllSessionfiles (xnatfolder, project, outputdir, True, host, connection, separate) 

    elif command == 'downloadSubject':
        if subject is None or project is None:
            print("Cannot download subject without a valid subject and project label. Please specify subject with --subject and  project with --project")
        else:
            filedown = downloadSubjectfiles (xnatfolder, project,subject, outputdir, True, host, connection)  

    elif command == 'downloadSubjectSessions':
        if subject is None or project is None:
            print("Cannot download subject without a valid subject and project label. Please specify subject with --subject and  project with --project")
        else:
            filedown = downloadSubjectSessionfiles (xnatfolder, project,subject, outputdir, True, host, connection, separate)  

    elif command == 'downloadProject':
        if project is None:
            print("Cannot download  Project without a valid project label. Please specify project  with --project")
        else:
            filedown = downloadProjectfiles (xnatfolder, project, outputdir, True, host, connection)

    elif command == 'downloadSessionDicomZip':
        if session is None or subject is None or project is None:
            print("Cannot download Session Dicoms without  a valid session, subject and project label. Please specify subject, session  and project with --subject, --session and --project respectively")
        else:
            filedown = downloadSessionDicomsZip ( project,subject, session,  outputdir, host, connection)
    else:
    	print("Do not recognize command passed. use downloadSession, downloadAllSessions, downloadSubject, downloadSubjectSessions, downloadProject or downloadSessionDicomZip")


    print("xnatDownload.py finished.")

# This is the standard boilerplate that calls the main() function.
if __name__ == '__main__':
    main()





