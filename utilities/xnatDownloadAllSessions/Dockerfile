# Use Ubuntu 16.04 LTS
FROM ubuntu:xenial-20161213

RUN mkdir -p /src /input /output /work

RUN apt update && \
    apt install -y zip curl wget

WORKDIR /tmp
RUN wget https://repo.anaconda.com/miniconda/Miniconda3-py38_4.10.3-Linux-x86_64.sh && \
 chmod +x Miniconda3-py38_4.10.3-Linux-x86_64.sh && \
 /bin/bash ./Miniconda3-py38_4.10.3-Linux-x86_64.sh -b -p /opt/miniconda -f && \
 export PATH=/opt/miniconda/bin:$PATH && \
 conda install -y pip

ENV PATH="/opt/miniconda/bin:${PATH}"

# Create a shared $HOME directory
RUN useradd -m -s /bin/bash -G users aacazxnat
WORKDIR /home/aacazxnat
ENV HOME="/home/aacazxnat"

WORKDIR /src
COPY ./xnatDownloadAllSessions.py /src/xnatDownloadAllSessions.py
ADD xnatutils.gz /src
ENV PATH="/src/:$PATH"
ENV TZ=America/Phoenix
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

#cleanup
RUN rm -rf /tmp/*

RUN ldconfig
WORKDIR /src
