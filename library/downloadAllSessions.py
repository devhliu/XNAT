from xnatutils.genutils import *
import os
__version__=0.1

def get_parser():
    from argparse import ArgumentParser
    from argparse import RawTextHelpFormatter
    parser = ArgumentParser(description="Download session files")
    parser.add_argument("--host", default="https://cnda.wustl.edu", help="CNDA host", required=True)
    parser.add_argument("--user", help="CNDA username", required=True)
    parser.add_argument("--password", help="Password", required=True)
    parser.add_argument("--project", help="Project ID", required=True)
    parser.add_argument("--resource", help="Resource Folder", required=True)
    parser.add_argument("--outputdir", help="Output Directory", required=False)
    parser.add_argument("--upload-by-ref", help="Upload \"by reference\". Only use if your host can read your file system.")
    return parser

def main():
    args, unknown_args = get_parser().parse_known_args()
    host = cleanServer(args.host)
    user = args.user
    password = args.password
    project = args.project
    resource = args.resource
    if args.outputdir is None:
        outputdir=os.path.join(os.getcwd(),'output')
    else:
        outputdir=os.path.abspath(args.outputdir)

    if not os.access(outputdir, os.R_OK):
        os.mkdir(outputdir)

    uploadByRef = isTrue(args.upload_by_ref)
    additionalArgs = unknown_args if unknown_args is not None else []

    connection = startSession(user,password)

    filedown = downloadAllSessionfiles (resource, project, outputdir, True, host, connection)

    print("DownloadAllSessions.py finished.")


# This is the standard boilerplate that calls the main() function.
if __name__ == '__main__':
    main()
