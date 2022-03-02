#!/bin/bash
tar czhf xnatutils.gz ./xnatutils
sudo docker build -t aacazxnat/xnatgetallsessions:0.1 .
docker push aacazxnat/xnatgetallsessions:0.1
