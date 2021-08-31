#!/bin/bash
#
# Build the singularity container.  

rm -f extract_audio_stream.sif
singularity build --fakeroot extract_audio_stream.sif extract_audio_stream.recipe
