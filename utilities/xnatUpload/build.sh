#!/bin/bash
tar czhf xnatutils.gz ./xnatutils
sudo docker build -t aacazxnat/xnatupload:0.1 .
docker push aacazxnat/xnatupload:0.1
