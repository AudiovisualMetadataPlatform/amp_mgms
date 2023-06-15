#!/bin/bash
#
# Copy the MGM source scripts & tool xmls to the destination 
destdir=${1:-unspecified}
if [ $destdir == "unspecified" ]; then
    echo "A destination directory must be specified"
    exit 1
fi

mkdir -p $destdir/tools/hmgms
cp -av  *.py *.xml task $destdir/tools/hmgms

