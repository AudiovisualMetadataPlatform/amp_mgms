#!/usr/bin/env amp_python.sif

import os
import os.path
import shutil
import subprocess
import sys
import tempfile
import argparse
import logging

import amp.utils
import amp.logging


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", default=False, action="store_true", help="Turn on debugging")
    parser.add_argument("--min_segment_duration", type=int, default=1000)
    parser.add_argument("input_audio")    
    parser.add_argument("amp_segments")
    args = parser.parse_args()
    amp.logging.setup_logging("applause_detection", args.debug)

    logging.info(f"Starting with args={args}")
    (input_audio, min_segment_duration, amp_segments) = (args.input_audio, args.min_segment_duration, args.amp_segments)    
    
    logging.debug("Current directory: " + os.getcwd())
    logging.debug("Input audio: " + input_audio)
    
    # use a tmp directory accessible to the singularity for input/output
    with tempfile.TemporaryDirectory() as tmpdir:
        # copy the input audio file to the tmp directory
        filename = os.path.basename(args.input_audio)
        shutil.copy(args.input_audio, f"{tmpdir}/{filename}")        
        
        # The applause_detection singularity file is assumed to be next to the 
        # script.
        sif = sys.path[0] + "/applause_detection.sif"

        # run singularity
        subprocess.run([sif, tmpdir, str(args.min_segment_duration)], check=True)

        # copy the corresponding temporary output file to the output AMP segments JSON        
        shutil.copy(f"{tmpdir}/{filename}.json", args.amp_segments)        
    logging.info("Finished")
    exit(0)

if __name__ == "__main__":
    main()
