# Use Ubuntu 16.04 LTS
FROM ubuntu:xenial-20161213

RUN mkdir -p /src /dicom /nifti /pyenv

RUN apt update && \
    apt install -y  build-essential zlib1g-dev libncurses5-dev libgdbm-dev libnss3-dev libssl-dev libreadline-dev libffi-dev libbz2-dev libsqlite3-dev llvm wget cmake git pigz nodejs-legacy npm python3 python3-pip python3-setuptools

WORKDIR /tmp
RUN wget https://www.python.org/ftp/python/3.7.3/Python-3.7.3.tgz
RUN tar -xf Python-3.7.3.tgz
WORKDIR /tmp/Python-3.7.3
RUN ./configure --enable-optimizations --enable-loadable-sqlite-extensions
RUN make -j 1 && \
    make altinstall

#set up python virtual environment
RUN pip3 install --upgrade pip
RUN pip3 install virtualenv
ENV VENV=/pyenv/py373
RUN mkdir $VENV
WORKDIR $VENV
RUN virtualenv -p /usr/local/bin/python3.7 $VENV
RUN . $VENV/bin/activate
ENV PATH="$VENV/bin:$PATH"

RUN npm install -g bids-validator

#Install dcm2niix from github
RUN cd /usr/local/src && \
    git clone https://github.com/rordenlab/dcm2niix.git && \
    cd dcm2niix && \
    git checkout tags/v1.0.20181125 -b install && \
    mkdir build  && \
    cd build && \
    cmake ..  && \
    make install 

#Install dcm2bids from github
RUN cd /usr/local/src && \
    git clone https://github.com/cbedetti/Dcm2Bids.git

RUN cd /usr/local/src/Dcm2Bids && \
    git checkout -f tags/2.1.4 

RUN cd /usr/local/src/Dcm2Bids && sed -i 's/datetime.now().isoformat()/(datetime.now() - datetime(1970,1,1)).total_seconds()/g' ./dcm2bids/dcm2bids.py    
RUN cd /usr/local/src/Dcm2Bids && pip install .

RUN pip install pybids \
                dicom \
                requests

WORKDIR /src
COPY ./bidsconvert-xnat.py /src
ENV PATH="/src/:$PATH"
ENV TZ=America/Phoenix
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN ldconfig
WORKDIR /tmp/

ARG BUILD_DATE
ARG DCM2BIDSVER
ARG VERSION
LABEL org.label-schema.build-date=$BUILD_DATE \
      org.label-schema.name="bidsconvert-xnat" \
      org.label-schema.description="Bids Conversion based on Dcm2Bids for aacazxnat" \
      org.label-schema.version=$VERSION \
      org.label-schema.url="https://github.com/MRIresearch/XNAT/blob/master/containers/bidsconvert-xnat/README.md" \
      org.label-schema.ref1-url="https://github.com/cbedetti/Dcm2Bids" \
      org.label-schema.ref1-ver=$DCM2BIDSVER \
      org.label-schema.schema-version="1.0"

LABEL org.nrg.commands="[{  \"name\": \"aacazxnat_bidsconvert-xnat\",  \"description\": \"Run DICOM to BIDS conversion using dcm2bids. Upload BIDS files at session level.\",  \"version\": \"0.1\",  \"schema-version\": \"1.0\",  \"image\": \"aacazxnat/bidsconvert-xnat:0.1\",  \"type\": \"docker\",  \"command-line\": \"python bidsconvert-xnat.py #SESSION_ID# #OVERWRITE# #SESSION_LABEL# --host \$XNAT_HOST --user \$XNAT_USER --pass \$XNAT_PASS --upload-by-ref False --dicomdir /dicom --niftidir /nifti\",  \"override-entrypoint\": true,  \"mounts\": [    {      \"name\": \"nifti\",      \"writable\": true,      \"path\": \"/nifti\"    }  ],  \"environment-variables\": {},  \"ports\": {},  \"inputs\": [    {      \"name\": \"session_id\",      \"description\": \"XNAT ID of the session\",      \"type\": \"string\",      \"matcher\": null,      \"default-value\": null,      \"required\": true,      \"replacement-key\": \"#SESSION_ID#\",      \"sensitive\": null,      \"command-line-flag\": \"--session\",      \"command-line-separator\": null,      \"true-value\": null,      \"false-value\": null    },    {      \"name\": \"overwrite\",      \"description\": \"Overwrite any existing NIFTI and BIDS scan resources?\",      \"type\": \"boolean\",      \"matcher\": null,      \"default-value\": \"true\",      \"required\": false,      \"replacement-key\": \"#OVERWRITE#\",      \"sensitive\": null,      \"command-line-flag\": \"--overwrite\",      \"command-line-separator\": null,      \"true-value\": \"True\",      \"false-value\": \"False\"    },    {      \"name\": \"session_label\",      \"description\": \"session label to use instead of default\",      \"type\": \"string\",      \"matcher\": null,      \"default-value\": null,      \"required\": false,      \"replacement-key\": \"#SESSION_LABEL#\",      \"sensitive\": null,      \"command-line-flag\": \"--session_label\",      \"command-line-separator\": null,      \"true-value\": null,      \"false-value\": null    }  ],  \"outputs\": [],  \"xnat\": [    {      \"name\": \"aacazxnat_bidsconvert-xnat\",      \"label\": null,      \"description\": \"Run DICOM to BIDS conversion at session-level using aacazxnat/bidsconvert-xnat:0.1\",      \"contexts\": [        \"xnat:imageSessionData\"      ],      \"external-inputs\": [        {          \"name\": \"session\",          \"description\": \"Input session\",          \"type\": \"Session\",          \"matcher\": null,          \"default-value\": null,          \"required\": true,          \"replacement-key\": null,          \"sensitive\": null,          \"provides-value-for-command-input\": null,          \"provides-files-for-command-mount\": null,          \"via-setup-command\": null,          \"user-settable\": null,          \"load-children\": true        }      ],      \"derived-inputs\": [        {          \"name\": \"session-id\",          \"description\": \"The session's id\",          \"type\": \"string\",          \"matcher\": null,          \"default-value\": null,          \"required\": true,          \"replacement-key\": null,          \"sensitive\": null,          \"provides-value-for-command-input\": \"session_id\",          \"provides-files-for-command-mount\": null,          \"user-settable\": null,          \"load-children\": true,          \"derived-from-wrapper-input\": \"session\",          \"derived-from-xnat-object-property\": \"id\",          \"via-setup-command\": null        }      ],      \"output-handlers\": []    }  ]}]"



