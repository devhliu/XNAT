import os 
import glob 
from shutil import copytree
from pathlib import Path
import argparse

# parse arguments
parser = argparse.ArgumentParser(description="organize dicoms for compressed upload")
parser.add_argument("inputDir", help="input directory")
parser.add_argument("outputDir", help="output directory")

args, unknown_args = parser.parse_known_args()



fulldicomdir=args.inputDir
newdicomdir=args.outputDir 


DICOMEXTS=['.IMA', '.DCM'] 
def isDicom(file): 
    extension=os.path.splitext(file)[1] 
    extensionUpper="" 
    if extension: 
        extensionUpper=extension.upper() 
    return extensionUpper in DICOMEXTS 


if not os.path.exists(newdicomdir): 
    os.mkdir(newdicomdir) 
newdicomdir=os.path.join(newdicomdir,'scans') 
if not os.path.exists(newdicomdir): 
    os.mkdir(newdicomdir)


scan_id=0 
for root, dirs, files in os.walk(fulldicomdir): 
    for dir in dirs: 
        files=glob.glob(os.path.join(root,dir,'*')) 
        if len(files)>0: 
            if isDicom(files[0]): 
                scan_id=scan_id + 1 
                scandir=os.path.join(newdicomdir,str(scan_id),'resources','DICOM') 
                scanpath=Path(scandir) 
                scanpath.mkdir(exist_ok=True, parents=True) 
                scanfiles=os.path.join(scandir,'files') 
                copytree(os.path.join(root,dir),scanfiles)
