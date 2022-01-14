#!/bin/bash
#
destdir=${1:-unspecified}
if [ $destdir == "unspecified" ]; then
    echo "A destination directory must be specified"
    exit 1
fi

mkdir -p $destdir/tools/amp_file
cp supplement.xml $destdir/tools/amp_file


