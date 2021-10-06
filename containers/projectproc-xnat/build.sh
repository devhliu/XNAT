#!/bin/bash
WORKDIR=.
CURRDIR=$PWD
rm -Rf ${WORKDIR}/bidsapps
mkdir -p ${WORKDIR}/bidsapps

cd ${WORKDIR}/bidsapps
git clone https://github.com/poldracklab/mriqc.git
cd ${WORKDIR}/bidsapps/mriqc
git checkout -f tags/0.15.2rc1

cd ${CURRDIR}
cp ${WORKDIR}/bidsapps/mriqc/Dockerfile .
cp ${WORKDIR}/bidsapps/mriqc/docker/files/neurodebian.gpg .

sed -i "s#ubuntu:xenial-20191010#nvidia/cuda:9.1-runtime-ubuntu16.04#g" ${WORKDIR}/Dockerfile
sed -i "s#COPY docker/files/neurodebian.gpg#COPY ${WORKDIR}/neurodebian.gpg#g" ${WORKDIR}/Dockerfile
sed -i "s#COPY requirements.txt#COPY ${WORKDIR}/bidsapps/mriqc/requirements.txt#g" ${WORKDIR}/Dockerfile 
sed -i "s#COPY . /src/mriqc#COPY ${WORKDIR}/bidsapps/mriqc/ /src/mriqc#g" ${WORKDIR}/Dockerfile
sed -i "s#COPY setup.cfg#COPY ${WORKDIR}/bidsapps/mriqc/setup.cfg#g" ${WORKDIR}/Dockerfile
sed -i 's/ENTRYPOINT/#ENTRYPOINT/g' ${WORKDIR}/Dockerfile
sed -i "/# Best practices/r${WORKDIR}/AddDocker" ${WORKDIR}/Dockerfile

# generate command flat file
cat orbisys-xnatqcaac-command_addParams.json | tr -d "\r" | tr -d "\n" > ${WORKDIR}/commandflat.json

sed -i 's^"^\\"^g' ${WORKDIR}/commandflat.json
sed -i 's^\$^\\$^g' ${WORKDIR}/commandflat.json

echo >> ${WORKDIR}/Dockerfile
echo -n 'LABEL org.nrg.commands="[' >> ${WORKDIR}/Dockerfile
cat ${WORKDIR}/commandflat.json >> ${WORKDIR}/Dockerfile
echo -e ']"\n' >> ${WORKDIR}/Dockerfile

VCS_REF=12451679
BUILD_DATE=$(date +%F)
VERSION=0.15.2
IMVER=0.1
docker build -t orbisys/xnataac_projectpreproc:${IMVER} --build-arg BUILD_DATE=${BUILD_DATE} --build-arg VERSION=${VERSION} --build-arg VCS_REF=${VCS_REF} .

docker push  orbisys/xnataac_projectpreproc:${IMVER}
