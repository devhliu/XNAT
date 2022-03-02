from xnatutils.genutils import *
import os
import getpass
__version__=0.1

def get_parser():
    from argparse import ArgumentParser
    from argparse import RawTextHelpFormatter
    parser = ArgumentParser(description="upload resource sto XNAT")
    parser.add_argument("command", default="uploadSession", help="uploadSession, uploadSubject, uploadProject")
    parser.add_argument("xnatfolder", default="DEFAULT-ORBISYS", help="collection name")
    parser.add_argument("extDir", default="./", help="source directory")
    parser.add_argument("--host", default="https://cnda.wustl.edu", help="CNDA host", required=True)
    parser.add_argument("--session", help="Session ID", required=False)
    parser.add_argument("--subject", help="subjecy ID", required=False)
    parser.add_argument("--project", help="Project", required=False)
    parser.add_argument("--user", help="user", required=False)
    parser.add_argument("--password", help="password", required=False)    
    parser.add_argument("--labels", default="DEFAULT,DEFAULT_FILES,DEFAULT", help="label values for uploaded files",  nargs='?', required=False)
    parser.add_argument("--overwrite", help="Overwrite NIFTI files if they exist")
    parser.add_argument("--upload-by-ref", help="Upload \"by reference\". Only use if your host can read your file system.")
    parser.add_argument('--version', action='version', version='%(prog)s 1')
    return parser



def main():
    args, unknown_args = get_parser().parse_known_args()
    host = cleanServer(args.host)
    
    command = args.command
    xnatfolder = args.xnatfolder
    extDir = args.extDir

    if args.user is None:
        user = input("User: ")
        args.user = user

    if args.password is None:
        password = getpass.getpass()
        args.password = password
    
    session = args.session
    subject = args.subject
    project = args.project
    labels = args.labels
    overwrite = isTrue(args.overwrite)
    uploadByRef = isTrue(args.upload_by_ref)
    additionalArgs = unknown_args if unknown_args is not None else []
    
    workflowId=None

    # Set up session
    connection = startSession(user,password)

    defaultlabels="DEFAULT,DEFAULT_FILES,DEFAULT".split(",")
    sublabels = labels.split(",")
    for counter, value in enumerate (sublabels):
        if counter > 2:
            break
        else:
            defaultlabels[counter]=value

    UPLOAD=False        

    if command == 'uploadSession':
        if session is None:
            print("Cannot upload session without a valid session label. Please specify session with --session")
        else:
            if checkSessionResource(xnatfolder,session,host, connection):
                print("Resource {} already exists for session {}".format(xnatfolder,session))
                if overwrite:
                    print("Will delete resource and overwrite.")
                    deleteFolder(workflowId, "/data/experiments/%s/resources/%s" % (session,xnatfolder), None,host,connection)
                    UPLOAD=True
                else:
                    print("Specify --overwrite='Y' to delete resource and complete upload.")
            else:
                UPLOAD=True

            if UPLOAD:
                print("Uploading Resource {} to session {}".format(xnatfolder,session))
                uploadfiles (workflowId , defaultlabels[0], defaultlabels[1] ,defaultlabels[2], extDir, "/data/experiments/%s/resources/%s/files" % (session, xnatfolder), host, connection, uploadByRef, args )
            else:
                print("upload aborted.")
    
     
    elif command == 'uploadSubject':
        if subject is None or project is None:
            print("Cannot upload subject resources without a valid subject and project label. Please specify subject with --subject and project with --project")
        else:
            if checkSubjectResource(xnatfolder,project,subject,host, connection):
                print("Resource {} already exists for subject {} in project {}".format(xnatfolder,subject,project))
                if overwrite:
                    print("Will delete resource and overwrite.")
                    deleteFolder(workflowId, "/data/projects/%s/subjects/%s/resources/%s" % (project,subject,xnatfolder), None,host,connection)
                    UPLOAD=True
                else:
                    print("Specify --overwrite='Y' to delete resource and complete upload.")
            else:
                UPLOAD=True

            if UPLOAD:
                print("Uploading Resource {} to subject {} in project {}".format(xnatfolder,subject, project))
                uploadfiles (workflowId , defaultlabels[0], defaultlabels[1] ,defaultlabels[2], extDir, "/data/projects/%s/subjects/%s/resources/%s/files" % (project, subject,xnatfolder),host, connection, uploadByRef, args )
            else:
                print("upload aborted.")
            
    elif command == 'uploadProject':
        if project is None:
            print("Cannot upload project without a valid project label. Please specify project with --project")
        else:
            if checkProjectResource(xnatfolder,project,host, connection):
                print("Resource {} already exists for project {}".format(xnatfolder,project))
                if overwrite:
                    print("Will delete resource and overwrite.")
                    deleteFolder(workflowId, "/data/projects/%s/resources/%s" % (project,xnatfolder), None,host,connection)
                    UPLOAD=True
                else:
                    print("Specify --overwrite='Y' to delete resource and complete upload.")
            else:
                UPLOAD=True

            if UPLOAD:
                print("Uploading Resource {} to  project {}".format(xnatfolder, project))
                uploadfiles (workflowId , defaultlabels[0], defaultlabels[1] ,defaultlabels[2], extDir, "/data/projects/%s/resources/%s/files" % (project, xnatfolder), host, connection, uploadByRef, args )
            else:
                print("upload aborted.")
            
    
    else:
    	print("Do not recognize command passed. use uploadSession, uploadSubject or uploadProject")


    print("xnatUpload.py finished.")


# This is the standard boilerplate that calls the main() function.
if __name__ == '__main__':
    main()


