# XNAT

Umbrella repository for managing and deploying neuroimaging containers and utilities for XNAT instance (aacazxnat)

## Containers

[bidsconvert-xnat](containers/bidsconvert-xnat/README.md) - This docker container uses [cbedetti/dcm2bids (version 2.1.4)](https://github.com/cbedetti/Dcm2Bids) and [pydeface (version 2.0.0)](https://github.com/poldracklab/pydeface) to convert DICOMS to bids. The main code heavilly borrows from the XNAT NRG implementation [dcm2bids-session](https://github.com/NrgXnat/docker-images/tree/master/dcm2bids-session) for critical functionality related to the download and upload of session files.

 

