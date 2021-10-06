# dicomUpload.py

Utility to iterate over dicom folders for multiple subjects and sessions and sequentially upload them to the XNAT instance.
Also provided as a docker image aacazxnat/dicomupload:0.1


# Introduction

The python executable `dicomUpdate.py` does the work to upload dicoms to the XNAT instance. It does this using `curl` and first compresses each dicom folder before sending it.


It is assumed that the dicom folders for multiple subjects is arranged as follows

```
testupload
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

 

