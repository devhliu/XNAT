#!/bin/bash
tar czhf xnatutils.gz ./xnatutils
sudo docker build -t aacazxnat/xnatgetsessionfiles:0.1 .
docker push aacazxnat/xnatgetsessionfiles:0.1
