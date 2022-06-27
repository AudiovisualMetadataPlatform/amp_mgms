#!/bin/env mco_python.sif
#
# Simple singularity container to extract an audio stream from an a/v file.
#
# Since this uses ffmpeg that isn't part of the default install, it has to be wrapped in a
# singularity container.

import argparse
import logging
from pathlib import Path
import subprocess
import amp.logger

def main():
    parser = argparse.ArgumentParser(description="Extract the audio stream from a file as-is")
    parser.add_argument('--debug', default=False, action='store_true', help="Turn on debugging")    
    parser.add_argument('avfile', help="Input A/V file")
    parser.add_argument('trimmedfile', help="Output filename")
    args = parser.parse_args()
    # use ffmpeg to remove trailing silence
    logging.info(f"Remove Trailing Silence args={args}")
    p = subprocess.run(['ffmpeg', '-y', 
                        '-loglevel','warning', 
                        '-i', args.avfile, 
                        '-af', "areverse,silenceremove=start_periods=1:start_duration=1:start_threshold=-60dB:detection=peak,aformat=s32,areverse",
                        '-f', 'wav', 
                        args.trimmedfile], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf-8")
    if p.returncode:
        logging.error(f"FFMPEG returned non-zero return code: {p.returncode}")
        logging.error(f"Output: {p.stderr}")
        exit(1)
    logging.info(f"Processing successful")
    exit(0)

if __name__ == "__main__":
    main()