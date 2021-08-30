#!/bin/bash
#
# Build a singularity container
rm extract_audio_stream.sif
singularity build --fakeroot extract_audio_stream.sif extract_audio_stream.recipe
