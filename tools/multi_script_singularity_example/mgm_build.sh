#!/bin/bash
#
# Build the singularity container.  
#

rm -f multi_script.sif
singularity build --fakeroot multi_script.sif multi_script.recipe
