#!/bin/bash
#
# Build the apptainer container.  

rm -f extract_audio_stream.sif
apptainer build --fakeroot extract_audio_stream.sif extract_audio_stream.recipe
