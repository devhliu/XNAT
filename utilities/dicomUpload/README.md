# dicomUpload.py

Utility to iterate over dicom folders for multiple subjects and sessions and sequentially upload them to the XNAT instance.
Also provided as a docker image aacazxnat/dicomupload:0.1


## Introduction

The python executable `dicomUpdate.py` does the work to upload dicoms to the XNAT instance. It does this using `curl` and first compresses each dicom folder before sending it.


It is assumed that the dicom folders for multiple subjects are arranged hierarchically. An example follows below for 2 subjects with ids 007 and 008 and sessions pre and post. These subjects will be uploaded to the designated project with subject ids of 007 and 008 and session ids of 007_post, 007_pre and 008_post, 008_pre.

```
dicomdir
├── 007
│   ├── post
│   │   ├── AAHEAD_SCOUT_MPR_SAG_0002
│   │   ├── JJWANGS_PCASL_0006
│   │   └── T1-MPRAGE_0011
│   └── pre
│       ├── T1-MPRAGE_ND_0010
│       └── T2_FLAIR_0012
└── 008
    ├── post
    │   ├── AAHEAD_SCOUT_MPR_SAG_0002
    │   ├── JJWANGS_PCASL_0006
    │   └── T1-MPRAGE_0011
    └── pre
        ├── T1-MPRAGE_ND_0010
        └── T2_FLAIR_0012
 ``` 
 ##  Calling dicomUpdate.py
 
 To call dicomUpdate.py directly you will need to have access to a python interpreter on an os that allows you command line access to `zip` and `curl`. Otherwise you can run a 
 docker version available as `aacazxnat/dicomupdate:0.1` that is packaged in an ubuntu container. 
 
 The direct call is shown below. The parameters passed are:
 
 * $URL = url location of xnat e.g. https://xnat.org
 * $USER = your user id to the xnat
 * $PASS = your password
 * $PROJECT = The project id you are adding dicoms to
 * $ROOTDIR = the top directory of dicom hierarchy. In our example aboce that would be `dicomdir`
 * $CONFIG = a configuration file for exclusion of dicoms. This will be explained in another section.
 
 ```
 python dicomUpload.py $URL $USER $PASS $PROJECT $ROOTDIR --config $CONFIG
 ```
 
 The docker call is similar to the above with the use of the `-v` parameter to bind locations from the host into the container. You will need to obtain the docker image first by doing the following `docker pull aacazxnat/dicomupload:0.1`
 
 ```
 docker run -it --rm -v $WORKDIR:/work -v $ROOTDIR:/dicom -v $PWD:/input aacazxnat/dicomupload:0.1 python /src/dicomUpload.py $URL $USER $PASS $PROJECT /dicom --config /input/$CONFIG  --workdir /work
 ```
 Examples of these calls are provided as `runuploadDocker.sh` and `runupload.sh`
 
 ## Excluding Dicoms
 You can exclude dicoms from the upload by including substrings that can be used to match the folders in a json file and passing this file in the `--config ` param. Here is an example of such a file which is provided as `Exclusions.json`. The two dicom folders `JJWANGS_PCASL_0006` and `AAHEAD_SCOUT_MPR_SAG_0002` will both be excluded from the upload using this config file.
 
 ```
 {
"Exclude":["Localizers","AAHEAD","MoCoSeries","JJWANGS"
    ]
}

```

 

