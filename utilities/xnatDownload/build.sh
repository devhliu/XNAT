#!/bin/bash
tar czhf xnatutils.gz ./xnatutils
sudo docker build -t aacazxnat/xnatdownload:0.1 .
docker push aacazxnat/xnatdownload:0.1
