# bidsconvert-xnat

Docker container aacazxnat/bidsconvert-xnat for converting dicoms to nifti files in bids format for the XNAT instance (aacazxnat).

## Introduction

This container uses [cbedetti/dcm2bids (version 2.1.4)](https://github.com/cbedetti/Dcm2Bids) which itself relies on [dcm2niix (version v1.0.20181125) ](https://github.com/rordenlab/dcm2niix) for the actual conversion from dicom to bids format.

[pydeface (version 2.0.0)](https://github.com/poldracklab/pydeface) whish relies on [FSL version 6.0.1](https://fsl.fmrib.ox.ac.uk/fsl/fslwiki) to deface T1w anatomicals.

The main code heavilly borrows from the XNAT NRG implementation [dcm2bids-session](https://github.com/NrgXnat/docker-images/tree/master/dcm2bids-session) for critical functionality related to the download and upload of session files.

To use this container simply pull it in the container service. If the command actions are not automatically applied then manually apply them from the file `aacazxnat_bidsconvert-xnat_command.json`

 

