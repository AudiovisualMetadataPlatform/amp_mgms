#!/bin/env python3
#
# Simple singularity container to extract an audio stream from an a/v file.
#
# Since this uses ffmpeg that isn't part of the default install, it has to be wrapped in a
# singularity container.

import argparse
import logging
from pathlib import Path
import subprocess

def main():
    parser = argparse.ArgumentParser(description="Extract the audio stream from a file as-is")
    parser.add_argument('--debug', default=False, action='store_true', help="Turn on debugging")    
    parser.add_argument('avfile', help="Input A/V file")
    parser.add_argument('trimmedfile', help="Output filename")
    args = parser.parse_args()
    logging.basicConfig(format="%(asctime)s [%(levelname)-8s] (%(filename)s:%(lineno)d)  %(message)s",
                        level=logging.DEBUG if args.debug else logging.INFO)    
    # use ffmpeg to extract the audio stream and put it into the file    
    p = subprocess.run(['ffmpeg', '-y', 
                        '-loglevel','warning', 
                        '-i', args.avfile, 
                        '-af', "areverse,silenceremove=start_periods=1:start_duration=1:start_threshold=-60dB:detection=peak,aformat=s32,areverse",
                        '-f', 'wav', 
                        args.trimmedfile])
    if p.returncode:
        logging.error(f"FFMPEG returned non-zero return code: {p.returncode}, args={args}")
        exit(1)
    logging.info(f"Processing successful, args={args}")
    exit(0)

if __name__ == "__main__":
    main()