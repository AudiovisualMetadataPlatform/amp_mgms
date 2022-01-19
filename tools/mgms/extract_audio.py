#!/bin/env mco_python.sif
# 
# Extract audio from a media file
#

import _preamble
import argparse
import logging
from pathlib import Path
import subprocess

def main():
    parser = argparse.ArgumentParser(description="Extract the audio stream from a file as-is")
    parser.add_argument('--debug', default=False, action='store_true', help="Turn on debugging")    
    parser.add_argument('avfile', help="Input A/V file")
    parser.add_argument('rate', type=int, help="Audio rate")
    parser.add_argument('channels', type=int, help="Audio channels")
    parser.add_argument('sample_format', help="Sample format (i.e. pcm_s16le)")
    parser.add_argument('audiostream', help="Output filename")
    args = parser.parse_args()    
    logging.getLogger().setLevel(logging.DEBUG if args.debug else logging.INFO)    
    # use ffmpeg to extract the audio stream and put it into the file
    logging.info(f"Extract Audio args={args}")
    p = subprocess.run(['ffmpeg', '-y', 
                        '-loglevel','warning', 
                        '-i', args.avfile, 
                        '-vn', 
                        '-c:a', args.sample_format,
                        '-ar', str(args.rate),
                        '-ac', str(args.channels), 
                        '-f', 'wav', 
                        args.audiostream])
    if p.returncode:
        logging.error(f"FFMPEG returned non-zero return code: {p.returncode}")
        exit(1)
    logging.info(f"Processing successful")
    exit(0)

if __name__ == "__main__":
    main()