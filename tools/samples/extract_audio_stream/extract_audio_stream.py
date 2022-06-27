#!/usr/bin/env mgm_python.sif
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
    parser.add_argument('audiostream', help="Output filename")
    args = parser.parse_args()
    logging.basicConfig(format="%(asctime)s [%(levelname)-8s] (%(filename)s:%(lineno)d)  %(message)s",
                        level=logging.DEBUG if args.debug else logging.INFO)
    logging.debug(f"avfile={args.avfile}, audiostream={args.audiostream}")
    
    # use ffmpeg to extract the audio stream and put it into an mkv file
    p = subprocess.run(['ffmpeg', '-y', '-loglevel','warning', '-i', args.avfile, '-vn', '-c:a', 'copy', '-f', 'matroska', args.audiostream])
    if p.returncode:
        logging.error(f"FFMPEG returned non-zero return code: {p.returncode}")
        exit(1)
    logging.info("Processing successful")
    

if __name__ == "__main__":
    main()