from xnatutils.genutils import *

__version__=0.1

def get_parser():
    from argparse import ArgumentParser
    from argparse import RawTextHelpFormatter
    parser = ArgumentParser(description="Run dcm2bids and pydeface on every file in a session")
    parser.add_argument("--host", default="https://cnda.wustl.edu", help="CNDA host", required=True)
    parser.add_argument("--user", help="CNDA username", required=True)
    parser.add_argument("--password", help="Password", required=True)
    parser.add_argument("--session", help="Session ID", required=False)
    parser.add_argument("--subject", help="Subject Label", required=False)
    parser.add_argument("--project", help="Project", required=False)
    parser.add_argument("--upload-by-ref", help="Upload \"by reference\". Only use if your host can read your file system.")
    return parser

def main():
    args, unknown_args = get_parser().parse_known_args()
    host = cleanServer(args.host)
    user = args.user
    password = args.password
    session = args.session
    subject = args.subject
    project = args.project
    uploadByRef = isTrue(args.upload_by_ref)
    additionalArgs = unknown_args if unknown_args is not None else []

    sesh = startSession(user,password)

    sublist = getSubjectFromSession(sesh, session, host)

    print(sublist)

    if project is None:
        project = getProjectFromSession(sesh, session, host)
    projdict = getProjectInfo(sesh, project, host)

    for key in projdict:
        print(key)

    #getProjectFromSession(sess, session, host

    OUTPUTDIR="/home/chidi/repos/XNAT/containers/bidsconvert-xnat/refactor/bidsdown"
    filedown = downloadSessionfiles ("BIDS-AACAZ", session, OUTPUTDIR, True, host, sesh)

    print("end")


# This is the standard boilerplate that calls the main() function.
if __name__ == '__main__':
    main()