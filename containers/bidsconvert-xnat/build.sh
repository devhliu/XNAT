#!/bin/bash
echo "Please login to Docker as aaxazxnat"
docker  login -u "aacazxnat" docker.io

IMVERFILE=/home/chidi/repos/XNAT/VERSION
IMVER=`cat $IMVERFILE`

WORKDIR=$PWD
BUILD_DATE=$(date +%F)
DCM2BIDSVER=2.1.4

# generate command flat file
sed -i "s^<<IMVER>>^${IMVER}^g" aacazxnat_bidsconvert-xnat_command.json 
cat aacazxnat_bidsconvert-xnat_command.json | tr -d "\r" | tr -d "\n" > ${WORKDIR}/commandflat.json

sed -i 's^"^\\"^g' ${WORKDIR}/commandflat.json
sed -i 's^\$^\\$^g' ${WORKDIR}/commandflat.json

cp ${WORKDIR}/BaseDockerfile ${WORKDIR}/Dockerfile

echo >> ${WORKDIR}/Dockerfile
echo -n 'LABEL org.nrg.commands="[' >> ${WORKDIR}/Dockerfile
cat ${WORKDIR}/commandflat.json >> ${WORKDIR}/Dockerfile
echo -e ']"\n' >> ${WORKDIR}/Dockerfile

docker build -t  aacazxnat/bidsconvert-xnat:${IMVER} --build-arg BUILD_DATE=${BUILD_DATE} --build-arg VERSION=${IMVER} --build-arg DCM2BIDSVER=${DCM2BIDSVER} .

docker push  aacazxnat/bidsconvert-xnat:${IMVER}

git tag -d v${IMVER}
git push origin --delete v${IMVER}
git tag v${IMVER}
git push origin v${IMVER}

