#!/usr/bin/env mgm_python.sif
# 
# Extract audio from a media file
#

import argparse
import logging
from pathlib import Path
import subprocess
import logging
import amp.logger

def main():
    parser = argparse.ArgumentParser(description="Extract the audio stream from a file as-is")
    parser.add_argument('--debug', default=False, action='store_true', help="Turn on debugging")    
    parser.add_argument('avfile', help="Input A/V file")
    parser.add_argument('rate', type=int, default=8000, help="Sample rate")
    parser.add_argument('channels', type=int, default=1, help="Number of channels")
    parser.add_argument('sample_format', default="pcm_s16le", help="Sample format (i.e. pcm_s16le)")
    parser.add_argument('audio_extracted', help="Audio Extracted")
    args = parser.parse_args()    
    logging.info(f"Starting with args {args}") 
    # use ffmpeg to extract the audio stream and put it into the file
    p = subprocess.run(['ffmpeg', '-y', 
                        '-loglevel','warning', 
                        '-i', args.avfile, 
                        '-vn', 
                        '-c:a', args.sample_format,
                        '-ar', str(args.rate),
                        '-ac', str(args.channels), 
                        '-f', 'wav', 
                        args.audio_extracted])
    if p.returncode:
        logging.error(f"FFMPEG returned non-zero return code: {p.returncode}")
        exit(1)
    logging.info("Finished.")
    exit(0)

if __name__ == "__main__":
    main()