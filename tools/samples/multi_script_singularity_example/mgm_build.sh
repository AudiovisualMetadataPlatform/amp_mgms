#!/bin/bash
#
# Build the apptainer container.  
#

rm -f multi_script.sif
apptainer build --fakeroot multi_script.sif multi_script.recipe
