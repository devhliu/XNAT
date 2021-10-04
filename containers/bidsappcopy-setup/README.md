# bidsappcopy-setup
Setup XNAT container for single subject, single session data for use with output of aacazxnat/bidsconvert-xnat

Simply clone this repository to a local folder and perform the following using a different name for your docker image:

`docker build -t aacazxnat/bidsappcopy-setup:1.0 .`

Following line is then required in Command script of the BIDS-App being run: 

`"via-setup-command": "aacazxnat/bidsappcopy-setup:1.0:bidsAppCopy",`

## Example scripts ##

two example scripts for mriqc (version 0.15.2rc1) are included in this repository. The second version of the command script
`mriqc_0.15.2.rc1_command-addparams.json` allows custom parameters to be passed. Examples of additional parameters are 
`--n_procs ${NUMPROCS} --ica`
