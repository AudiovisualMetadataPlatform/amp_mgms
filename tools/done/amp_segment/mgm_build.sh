#!/bin/bash
#
# Build the singularity container.  
destdir=${1:-unspecified}
if [ $destdir == "unspecified" ]; then
    echo "A destination directory must be specified"
    exit 1
fi

echo "Not finished."
exit 0
make DESTDIR=$destdir install


