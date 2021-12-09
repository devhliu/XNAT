FROM poldracklab/mriqc:0.16.1

RUN apt-get update 
RUN apt-get install -y xvfb \
                       wget

#install CUDA libraries for 9.1
ENV LD_LIBRARY_PATH=/usr/local/cuda/lib64:/usr/lib:$LD_LIBRARY_PATH
ENV PATH=/usr/local/cuda/bin:$PATH

#install CUDA 9.1
WORKDIR /tmp
RUN wget https://developer.nvidia.com/compute/cuda/9.1/Prod/local_installers/cuda_9.1.85_387.26_linux && \
mkdir -p /tmp/nvidia_installers && \
chmod +x cuda_9.1.85_387.26_linux && \
 ./cuda_9.1.85_387.26_linux -extract=`pwd`/nvidia_installers && \
rm cuda_9.1.85_387.26_linux

WORKDIR /tmp/nvidia_installers
RUN ./cuda*.run --tar mxvf && \
 cp InstallUtils.pm /usr/lib/x86_64-linux-gnu/perl-base && \
 rm cuda-samples* && \
 rm NVIDIA-Linux* && \
 ./cuda-linux.9.1.85-23083092.run -noprompt && \
 wget https://developer.nvidia.com/compute/cuda/9.1/Prod/patches/1/cuda_9.1.85.1_linux && \
 chmod +x cuda_9.1.85.1_linux && \
./cuda_9.1.85.1_linux --silent -accept-eula && \
 wget https://developer.nvidia.com/compute/cuda/9.1/Prod/patches/2/cuda_9.1.85.2_linux && \
 chmod +x cuda_9.1.85.2_linux && \
 ./cuda_9.1.85.2_linux --silent -accept-eula && \
 wget https://developer.nvidia.com/compute/cuda/9.1/Prod/patches/3/cuda_9.1.85.3_linux && \
 chmod +x cuda_9.1.85.3_linux && \
 ./cuda_9.1.85.3_linux --silent -accept-eula 
WORKDIR /tmp 
RUN rm -R nvidia_installers


#install FSL 6.0.3
RUN apt-get update
RUN apt-get install -y python-pip
ENV FSLDIR=/opt/fsl603
WORKDIR /opt
RUN wget https://fsl.fmrib.ox.ac.uk/fsldownloads/fslinstaller.py
RUN python2.7 fslinstaller.py -q -d $FSLDIR -V 6.0.3

# append to end of path to gain access to Eddy
ENV PATH="$PATH:$FSLDIR/bin"


RUN apt update && \
    apt install -y cmake git pigz


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


WORKDIR /opt
RUN git clone https://github.com/poldracklab/pydeface.git 
WORKDIR /opt/pydeface
RUN git checkout -f tags/v1.1.0
RUN python setup.py install

ENV PATH=/opt/pydeface:$PATH


# additional python dependencies for qcsession-xnat.py; several like pybids aready fulfilled by mriqc
RUN pip install requests==2.23.0 

RUN mkdir -p /src /dicom /nifti /bids

# download freesurfer license
WORKDIR /src
ENV PATH="/src/:$PATH"
RUN wget https://www.dropbox.com/s/40wxja0xqw409ra/license.txt

RUN export TZ=America/Phoenix && \
    ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone


# workaround for GPUs?
ENV NVIDIA_VISIBLE_DEVICES=all

# install mrtrix
RUN apt-get install -y dc \
        libqt5opengl5-dev \
        libqt5svg5-dev \
        libtiff5-dev \
        git \
        g++ \
        libeigen3-dev \
        zlib1g-dev \
        libqt4-opengl-dev \
        libgl1-mesa-dev \
        libfftw3-dev

WORKDIR /opt
RUN git clone https://github.com/MRtrix3/mrtrix3.git
WORKDIR /opt/mrtrix3
RUN ./configure && \
    ./build

ENV PATH=/opt/mrtrix3/bin:$PATH

# copy in source code
WORKDIR /src
COPY ./qcproject-xnat.py /src
COPY ./xnatutils /src/xnatutils

# Best practices
RUN ldconfig
WORKDIR /tmp/

#https://stackoverflow.com/questions/41207522/docker-override-or-remove-entrypoint-from-a-base-image
ENTRYPOINT ["/usr/bin/env"]

LABEL org.nrg.commands="[{  \"name\": \"aacazxnat_qcproject-xnat-0.1\",  \"description\": \"Run QC pipeline at project level.\",  \"version\": \"0.1\",  \"schema-version\": \"1.0\",  \"image\": \"orbisys/qcproject-xnat:0.1\",  \"type\": \"docker\",  \"command-line\": \"python /src/qcproject-xnat.py #PROJECT_ID# #OVERWRITE# --host \$XNAT_HOST --user \$XNAT_USER --pass \$XNAT_PASS --upload-by-ref False --cleanup True --proc_steps '#PROC_STEPS#' --dicomdir /dicom --niftidir /nifti\",  \"override-entrypoint\": true,  \"mounts\": [    {      \"name\": \"nifti\",      \"writable\": true,      \"path\": \"/nifti\"    }  ],  \"environment-variables\": {},  \"ports\": {},  \"inputs\": [    {      \"name\": \"project_id\",      \"description\": \"XNAT ID of the project\",      \"type\": \"string\",      \"matcher\": null,      \"default-value\": null,      \"required\": true,      \"replacement-key\": \"#PROJECT_ID#\",      \"sensitive\": null,      \"command-line-flag\": \"--project\",      \"command-line-separator\": null,      \"true-value\": null,      \"false-value\": null    },    {      \"name\": \"overwrite\",      \"description\": \"Overwrite any existing NIFTI and BIDS scan resources?\",      \"type\": \"boolean\",      \"matcher\": null,      \"default-value\": \"true\",      \"required\": false,      \"replacement-key\": \"#OVERWRITE#\",      \"sensitive\": null,      \"command-line-flag\": \"--overwrite\",      \"command-line-separator\": null,      \"true-value\": \"True\",      \"false-value\": \"False\"    },    {      \"name\": \"proc_steps\",      \"description\": \"additional processing steps\",      \"type\": \"string\",      \"matcher\": null,      \"default-value\": null,      \"required\": false,      \"replacement-key\": \"#PROC_STEPS#\",      \"sensitive\": null,      \"command-line-flag\": null,      \"command-line-separator\": null,      \"true-value\": null,      \"false-value\": null    }  ],  \"outputs\": [],  \"xnat\": [    {      \"name\": \"aacazxnat_qcproject-xnat-0.1\",      \"label\": null,      \"description\": \"Run QC pipeline at projectlevel using aacazxnat/qcproject-xnat:0.1\",      \"contexts\": [        \"xnat:projectData\"      ],      \"external-inputs\": [        {          \"name\": \"project\",          \"description\": \"Input project\",          \"type\": \"Project\",          \"matcher\": null,          \"default-value\": null,          \"required\": true,          \"replacement-key\": null,          \"sensitive\": null,          \"provides-value-for-command-input\": null,          \"provides-files-for-command-mount\": null,          \"via-setup-command\": null,          \"user-settable\": null,          \"load-children\": true        }      ],      \"derived-inputs\": [        {          \"name\": \"project-id\",          \"description\": \"The project's id\",          \"type\": \"string\",          \"matcher\": null,          \"default-value\": null,          \"required\": true,          \"replacement-key\": null,          \"sensitive\": null,          \"provides-value-for-command-input\": \"project_id\",          \"provides-files-for-command-mount\": null,          \"user-settable\": null,          \"load-children\": true,          \"derived-from-wrapper-input\": \"project\",          \"derived-from-xnat-object-property\": \"id\",          \"via-setup-command\": null        }      ],      \"output-handlers\": []    }  ]}]"

