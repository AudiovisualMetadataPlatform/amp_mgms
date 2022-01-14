#!/bin/bash
#
# Build the mgm_python singularity container.  
destdir=${1:-unspecified}
if [ $destdir == "unspecified" ]; then
    echo "A destination directory must be specified"
    exit 1
fi

make DESTDIR=$destdir install


