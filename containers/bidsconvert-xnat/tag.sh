#!/bin/bash
IMVERFILE=/home/chidi/repos/XNAT/VERSION
IMVER=`cat $IMVERFILE`
echo "tagging repository to version $IMVER. continue?"
read dummy

git tag -d v${IMVER}
git push origin --delete v${IMVER}
git tag v${IMVER}
git push origin v${IMVER}

