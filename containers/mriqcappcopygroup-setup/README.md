# bidsappcopygroup-setup
Docker container to enable bidsapps to work at the project level.

## Overview
It is assumed that bids conversions have already been performed at the session level by using the docker image 
`aacazxnat/bidsconvert-xnat:1.0` as detailed in repository bidsconvert-xnat.

This will create a resource BIDS  refererence at the session level under `BIDS-AACAZ/sub*`

The container referenced here can then be used hopefully as a setup-container to collect the BIDS sub-directories for all subjects
for presentation to a BIDS-compatible app like mriqc etc.


## Use

On your xnat system you can pull aacazxnat/bidsappcopygroup-setup:1.0 and then include in the bids app as a setup command
in the command script as follows:

`"via-setup-command": "aacazxnat/bidsappcopygroup-setup:1.0:bidsAppCopyGroupAAC",`

two example scripts for mriqc (version 0.15.2rc1) are included in this repository. The second version of the command script
`mriqc_0.15.2.rc1_command-addparams.json` allows custom parameters to be passed. Examples of additional parameters are 
`--n_procs ${NUMPROCS} --ica`


## Build Docker Image

To insulate yourself from changes to this container you may want to build your own copy. Follow steps bnelow to accom[plish this.

Navigate to an empty folder on your system and build and push the image. You will of course have to call it something else and not aacazxnat/bidscopygroup-setup:1.0

`git clone https://github.com/MRIresearch/XNAT

`cd XNAT/containers/bidsappcopygroup-setup`

`docker build -t aacazxnat/bidsappcopygroup-setup:1.0 .`
