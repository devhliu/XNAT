#!/bin/bash
WORKDIR=$PWD

cat aacazxnat_qcproject-xnat_command.json | tr -d "\r" | tr -d "\n" > ${WORKDIR}/commandflat.json

sed -i 's^"^\\"^g' ${WORKDIR}/commandflat.json
sed -i 's^\$^\\$^g' ${WORKDIR}/commandflat.json

cp ${WORKDIR}/AddDocker ${WORKDIR}/Dockerfile

echo >> ${WORKDIR}/Dockerfile
echo -n 'LABEL org.nrg.commands="[' >> ${WORKDIR}/Dockerfile
cat ${WORKDIR}/commandflat.json >> ${WORKDIR}/Dockerfile
echo -e ']"\n' >> ${WORKDIR}/Dockerfile

IMVER=0.1
docker build -t aacazxnat/qcproject-xnat:${IMVER} .

docker push  aacazxnat/qcproject-xnat:${IMVER}
