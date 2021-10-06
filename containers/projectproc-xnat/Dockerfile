# Use Ubuntu 16.04 LTS
FROM nvidia/cuda:9.1-runtime-ubuntu16.04

# Pre-cache neurodebian key
COPY ./neurodebian.gpg /usr/local/etc/neurodebian.gpg

# Installing Neurodebian packages (FSL, AFNI, git)
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* && \
    curl -sSL "http://neuro.debian.net/lists/xenial.us-ca.full" >> /etc/apt/sources.list.d/neurodebian.sources.list && \
    apt-key add /usr/local/etc/neurodebian.gpg && \
    (apt-key adv --refresh-keys --keyserver hkp://ha.pool.sks-keyservers.net 0xA5D32F012649A5A9 || true)

# Prepare environment
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
                    autoconf \
                    build-essential \
                    bzip2 \
                    ca-certificates \
                    curl \
                    cython3 \
                    ed \
                    git \
                    git-annex-standalone \
                    graphviz=2.38.0-12ubuntu2 \
                    gsl-bin \
                    libglib2.0-0 \
                    libglu1-mesa-dev \
                    libglw1-mesa \
                    libgomp1 \
                    libjpeg62 \
                    libtool \
                    libxm4 \
                    netpbm \
                    pkg-config \
                    tcsh \
                    xfonts-base \
                    xvfb \
                    fsl-core=5.0.9-5~nd16.04+1 \
                    fsl-mni152-templates && \
    curl -sSL https://deb.nodesource.com/setup_10.x | bash - && \
    apt-get install -y --no-install-recommends \
                    nodejs && \
    echo "Install libxp (not in all ubuntu/debian repositories)" && \
    apt-get install -yq --no-install-recommends libxp6 \
    || /bin/bash -c " \
       curl --retry 5 -o /tmp/libxp6.deb -sSL http://mirrors.kernel.org/debian/pool/main/libx/libxp/libxp6_1.0.2-2_amd64.deb \
       && dpkg -i /tmp/libxp6.deb && rm -f /tmp/libxp6.deb" && \
    echo "Install libpng12 (not in all ubuntu/debian repositories" && \
    apt-get install -yq --no-install-recommends libpng12-0 \
    || /bin/bash -c " \
       curl -o /tmp/libpng12.deb -sSL http://mirrors.kernel.org/debian/pool/main/libp/libpng/libpng12-0_1.2.49-1%2Bdeb7u2_amd64.deb \
       && dpkg -i /tmp/libpng12.deb && rm -f /tmp/libpng12.deb" && \
    ln -s /usr/lib/x86_64-linux-gnu/libgsl.so.19 /usr/lib/x86_64-linux-gnu/libgsl.so.0 && \
    ldconfig && \
    apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

ENV FSLDIR="/usr/share/fsl/5.0" \
    FSLOUTPUTTYPE="NIFTI_GZ" \
    FSLMULTIFILEQUIT="TRUE" \
    POSSUMDIR="/usr/share/fsl/5.0" \
    LD_LIBRARY_PATH="/usr/lib/fsl/5.0:$LD_LIBRARY_PATH" \
    FSLTCLSH="/usr/bin/tclsh" \
    FSLWISH="/usr/bin/wish"
ENV PATH="/usr/lib/fsl/5.0:/usr/lib/afni/bin:$PATH"

# Installing ANTs 2.2.0 (NeuroDocker build)
ENV ANTSPATH=/usr/lib/ants
RUN mkdir -p $ANTSPATH && \
    curl -sSL "https://dl.dropbox.com/s/2f4sui1z6lcgyek/ANTs-Linux-centos5_x86_64-v2.2.0-0740f91.tar.gz" \
    | tar -xzC $ANTSPATH --strip-components 1
ENV PATH=$ANTSPATH:$PATH

# Installing AFNI (version 17_3_03 archived on OSF)
RUN mkdir -p /opt/afni && \
    curl -o afni.tar.gz -sSLO "https://files.osf.io/v1/resources/fvuh8/providers/osfstorage/5a0dd9a7b83f69027512a12b" && \
    tar zxv -C /opt/afni --strip-components=1 -f afni.tar.gz && \
    rm -rf afni.tar.gz
ENV PATH=/opt/afni:$PATH \
    AFNI_MODELPATH="/opt/afni/models" \
    AFNI_IMSAVE_WARNINGS="NO" \
    AFNI_TTATLAS_DATASET="/opt/afni/atlases" \
    AFNI_PLUGINPATH="/opt/afni/plugins"

# Create a shared $HOME directory
RUN useradd -m -s /bin/bash -G users bidsapp
WORKDIR /home/bidsapp
ENV HOME="/home/bidsapp"

# Installing SVGO
RUN npm install -g svgo

# Installing and setting up miniconda
RUN curl -sSLO https://repo.continuum.io/miniconda/Miniconda3-4.5.11-Linux-x86_64.sh && \
    bash Miniconda3-4.5.11-Linux-x86_64.sh -b -p /usr/local/miniconda && \
    rm Miniconda3-4.5.11-Linux-x86_64.sh

# Set CPATH for packages relying on compiled libs (e.g. indexed_gzip)
ENV PATH="/usr/local/miniconda/bin:$PATH" \
    CPATH="/usr/local/miniconda/include/:$CPATH" \
    LANG="C.UTF-8" \
    LC_ALL="C.UTF-8" \
    PYTHONNOUSERSITE=1
# Consider PYTHONWARNINGS="ignore,default:::mriqc,default:::nipype"

# Installing precomputed python packages
RUN conda install -y python=3.7.1 \
                     graphviz=2.40.1 \
                     libxml2=2.9.8 \
                     libxslt=1.1.32 \
                     matplotlib=2.2.2 \
                     mkl-service \
                     mkl=2018.0.3 \
                     numpy=1.15.4 \
                     pandas=0.23.4 \
                     scikit-learn=0.19.1 \
                     scipy=1.1.0 \
                     setuptools>=40.0.0 \
                     traits=4.6.0 \
                     pip=19.1 \
                     zlib; sync && \
    chmod -R a+rX /usr/local/miniconda; sync && \
    chmod +x /usr/local/miniconda/bin/*; sync && \
    conda build purge-all; sync && \
    conda clean -tipsy && sync

# Unless otherwise specified each process should only use one thread - nipype
# will handle parallelization
ENV MKL_NUM_THREADS=1 \
    OMP_NUM_THREADS=1

# Precaching fonts, set 'Agg' as default backend for matplotlib
RUN python -c "from matplotlib import font_manager" && \
    sed -i 's/\(backend *: \).*$/\1Agg/g' $( python -c "import matplotlib; print(matplotlib.matplotlib_fname())" )


# Installing dev requirements (packages that are not in pypi)
WORKDIR /src/

# Precaching atlases
COPY ./bidsapps/mriqc/setup.cfg setup.cfg
RUN pip install --no-cache-dir "$( grep templateflow setup.cfg | xargs )" && \
    python -c "from templateflow import api as tfapi; \
               tfapi.get('MNI152NLin2009cAsym', resolution=[1, 2], suffix='T1w', desc=None); \
               tfapi.get('MNI152NLin2009cAsym', resolution=[1, 2], suffix='mask',\
                         desc=['brain', 'head']); \
               tfapi.get('MNI152NLin2009cAsym', resolution=1, suffix='dseg', desc='carpet'); \
               tfapi.get('MNI152NLin2009cAsym', resolution=1, suffix='probseg',\
                         label=['CSF', 'GM', 'WM']);\
               tfapi.get('MNI152NLin2009cAsym', resolution=[1, 2], suffix='boldref')" && \
    rm setup.cfg

# Installing MRIQC
COPY ./bidsapps/mriqc/ /src/mriqc
ARG VERSION
# Force static versioning within container
RUN echo "${VERSION}" > /src/mriqc/mriqc/VERSION && \
    echo "include mriqc/VERSION" >> /src/mriqc/MANIFEST.in && \
    cd /src/mriqc && \
    pip install --no-cache-dir .[all]

RUN find $HOME -type d -exec chmod go=u {} + && \
    find $HOME -type f -exec chmod go=u {} +

# Best practices
RUN apt-get update 
RUN apt-get install -y xvfb \
                       wget

#install CUDA libraries for 9.1
ENV LD_LIBRARY_PATH=/usr/local/cuda/lib64:/usr/lib:$LD_LIBRARY_PATH
ENV PATH=/usr/local/cuda/bin:$PATH

#install FSL 6.0.1
RUN apt-get update
RUN apt-get install -y python-pip
ENV FSLDIR=/opt/fsl601
WORKDIR /opt
RUN wget https://fsl.fmrib.ox.ac.uk/fsldownloads/fslinstaller.py
RUN python2.7 fslinstaller.py -q -d $FSLDIR -V 6.0.1

# append to end of path to gain access to Eddy
ENV PATH="$PATH:$FSLDIR/bin"

# Reset SFSLDIR
ENV FSLDIR=/usr/share/fsl/5.0

RUN apt update && \
    apt install -y  cmake git pigz

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

RUN cd /usr/local/src/Dcm2Bids checkout -f tags/1.5.1rc2 && \
    git checkout -f tags/2.1.4

RUN cd /usr/local/src/Dcm2Bids && sed -i 's/datetime.now().isoformat()/(datetime.now() - datetime(1970,1,1)).total_seconds()/g' ./dcm2bids/dcm2bids.py    
RUN cd /usr/local/src/Dcm2Bids && pip install .

RUN pip install \
        dicom \
        nipype \
        requests \
        pybids 

RUN mkdir -p /dicom /bids

RUN pip install \
        nibabel 

WORKDIR /opt
RUN git clone https://github.com/poldracklab/pydeface.git 
WORKDIR /opt/pydeface
RUN python setup.py install

ENV PATH=/opt/pydeface:$PATH

WORKDIR /src
COPY ./xnatProject_master.py /src
ENV PATH="/src/:$PATH"

WORKDIR /tmp
RUN wget https://www.dropbox.com/s/40wxja0xqw409ra/license.txt

RUN ldconfig
WORKDIR /tmp/
RUN ldconfig
WORKDIR /tmp/

# Run mriqc by default
#ENTRYPOINT ["/usr/local/miniconda/bin/mriqc"]

ARG BUILD_DATE
ARG VCS_REF
LABEL org.label-schema.build-date=$BUILD_DATE \
      org.label-schema.name="MRIQC" \
      org.label-schema.description="MRIQC - Automated Quality Control and visual reports for Quality Assesment of structural (T1w, T2w) and functional MRI of the brain" \
      org.label-schema.url="http://mriqc.readthedocs.io" \
      org.label-schema.vcs-ref=$VCS_REF \
      org.label-schema.vcs-url="https://github.com/poldracklab/mriqc" \
      org.label-schema.version=$VERSION \
      org.label-schema.schema-version="1.0"

LABEL org.nrg.commands="[{  \"name\": \"xnat-orbisys-xnatqcaac-project-01\",  \"description\": \"Runs QC pipeline at project level.\",  \"version\": \"1.0\",  \"schema-version\": \"1.0\",  \"image\": \"orbisys/xnataac_projectpreproc:0.1\",  \"type\": \"docker\",  \"command-line\": \"xnatProject_master.py #PROJECT_ID# #OVERWRITE# --host \$XNAT_HOST --user \$XNAT_USER --pass \$XNAT_PASS --upload-by-ref False --proc_steps '#PROC_STEPS#' --eddy_params '#EDDY_PARAMS#' --mriqc_params '#MRIQC_PARAMS#' --fmriprep_params '#FMRIPREP_PARAMS#' --dicomdir /dicom --niftidir /nifti\",  \"override-entrypoint\": true,  \"mounts\": [    {      \"name\": \"nifti\",      \"writable\": true,      \"path\": \"/nifti\"    }  ],  \"environment-variables\": {},  \"ports\": {},  \"inputs\": [    {      \"name\": \"project_id\",      \"description\": \"XNAT ID of the project\",      \"type\": \"string\",      \"matcher\": null,      \"default-value\": null,      \"required\": true,      \"replacement-key\": \"#PROJECT_ID#\",      \"sensitive\": null,      \"command-line-flag\": \"--project\",      \"command-line-separator\": null,      \"true-value\": null,      \"false-value\": null    },    {      \"name\": \"overwrite\",      \"description\": \"Overwrite any existing NIFTI and BIDS scan resources?\",      \"type\": \"boolean\",      \"matcher\": null,      \"default-value\": \"true\",      \"required\": false,      \"replacement-key\": \"#OVERWRITE#\",      \"sensitive\": null,      \"command-line-flag\": \"--overwrite\",      \"command-line-separator\": null,      \"true-value\": \"True\",      \"false-value\": \"False\"    },    {      \"name\": \"proc_steps\",      \"description\": \"additional processing steps\",      \"type\": \"string\",      \"matcher\": null,      \"default-value\": null,      \"required\": false,      \"replacement-key\": \"#PROC_STEPS#\",      \"sensitive\": null,      \"command-line-flag\": null,      \"command-line-separator\": null,      \"true-value\": null,      \"false-value\": null    },    {      \"name\": \"mriqc_params\",      \"description\": \"additional mriqc params\",      \"type\": \"string\",      \"matcher\": null,      \"default-value\": null,      \"required\": false,      \"replacement-key\": \"#MRIQC_PARAMS#\",      \"sensitive\": null,      \"command-line-flag\": null,      \"command-line-separator\": null,      \"true-value\": null,      \"false-value\": null    },    {      \"name\": \"fmriprep_params\",      \"description\": \"additional fmriprep params\",      \"type\": \"string\",      \"matcher\": null,      \"default-value\": null,      \"required\": false,      \"replacement-key\": \"#FMRIPREP_PARAMS#\",      \"sensitive\": null,      \"command-line-flag\": null,      \"command-line-separator\": null,      \"true-value\": null,      \"false-value\": null    },    {      \"name\": \"eddy_params\",      \"description\": \"additional fsl params\",      \"type\": \"string\",      \"matcher\": null,      \"default-value\": null,      \"required\": false,      \"replacement-key\": \"#EDDY_PARAMS#\",      \"sensitive\": null,      \"command-line-flag\": null,      \"command-line-separator\": null,      \"true-value\": null,      \"false-value\": null    }  ],  \"outputs\": [],  \"xnat\": [    {      \"name\": \"xnat-orbisys-xnatqcaac-project-01\",      \"label\": null,      \"description\": \"Run QC pipeline orbisys/xnatqcaac on a Project - version 01\",      \"contexts\": [        \"xnat:projectData\"      ],      \"external-inputs\": [        {          \"name\": \"project\",          \"description\": \"Input project\",          \"type\": \"Project\",          \"matcher\": null,          \"default-value\": null,          \"required\": true,          \"replacement-key\": null,          \"sensitive\": null,          \"provides-value-for-command-input\": null,          \"provides-files-for-command-mount\": null,          \"via-setup-command\": null,          \"user-settable\": null,          \"load-children\": true        }      ],      \"derived-inputs\": [        {          \"name\": \"project-id\",          \"description\": \"The project's id\",          \"type\": \"string\",          \"matcher\": null,          \"default-value\": null,          \"required\": true,          \"replacement-key\": null,          \"sensitive\": null,          \"provides-value-for-command-input\": \"project_id\",          \"provides-files-for-command-mount\": null,          \"user-settable\": null,          \"load-children\": true,          \"derived-from-wrapper-input\": \"project\",          \"derived-from-xnat-object-property\": \"id\",          \"via-setup-command\": null        }      ],      \"output-handlers\": []    }  ]}]"

