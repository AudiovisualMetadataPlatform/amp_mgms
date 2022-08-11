#!/bin/bash

# find out where this script is running from
HERE=$(dirname $(readlink -f ${BASH_SOURCE[0]}))
export PATH=/sbin:/usr/sbin:/usr/local/sbin:$PATH

# check our parameters
if [ "x$1" == "x" -o "x$2" == "x" ]; then
    echo "Usage: $0 <mode> <audio file path>"
    exit 1
fi

ENV=$1
case $ENV in
    [cg]pu)
        if [ ! -e $HERE/kaldi-pua-$ENV.sif ]; then
            echo "The container for this environment has not been built -- build it using build_singularity.sh"
            exit 3
        fi

        ;;
    *)
        echo "Mode must be 'cpu' or 'gpu'"
        exit 2
    ;;
esac


SOURCE=$(realpath $2)
if [ ! -d $SOURCE ]; then
    echo "ERROR:  '$SOURCE' is not a directory"    
    exit 2
fi


# get a reasonable value for TMPDIR
if [ "x$TMPDIR" == "x" ]; then
    TMPDIR="/tmp"
fi

# create a sparse overlay filesystem
# Even though it looks like it is 100G on the disk, it is a sparse file, 
# so it is only using whatever a blank filesystem takes + the contents:
# whatever the kaldi processes write to places OTHER than /audio_in
OVERLAY=$TMPDIR/kaldi-overlay-$$.ext3
dd if=/dev/zero of=$OVERLAY bs=1K count=1 seek=100M 
mkfs.ext3 -F $OVERLAY

# run the singularity container
echo "Running $ENV version of kaldi"
singularity run -B $SOURCE:/audio_in --overlay $OVERLAY $HERE/kaldi-pua-$ENV.sif 


# clean up
rm $OVERLAY