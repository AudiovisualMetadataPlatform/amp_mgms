#!/usr/bin/env amp_python.sif
#
# Extract the audio stream from an a/v file as a wav file.

import argparse
import logging
from pathlib import Path
import subprocess

def main():
    parser = argparse.ArgumentParser(description="Extract the audio stream as a wav file")
    parser.add_argument('--debug', default=False, action='store_true', help="Turn on debugging") 
    parser.add_argument('--channels', default='2', choices=['1', '2'], help="Number of channels")
    parser.add_argument('--rate', default='44100', choices=['8000', '16000', '22050', '44100', '48000', '96000'], help="Sample Rate")
    parser.add_argument('--size', default='16', choices=['16', '24'], help="Sample size")
    parser.add_argument('avfile', help="Input A/V file")
    parser.add_argument('audiostream', help="Output filename")
    args = parser.parse_args()
    logging.basicConfig(format="%(asctime)s [%(levelname)-8s] (%(filename)s:%(lineno)d)  %(message)s",
                        level=logging.DEBUG if args.debug else logging.INFO)
    logging.debug(f"avfile={args.avfile}, audiostream={args.audiostream}")
        
    cmd = [
        'ffmpeg', '-y', '-hide_banner', '-nostats', '-loglevel', 'panic',
        '-i', args.avfile, 
        '-ar', args.rate,
        '-ac', args.channels,
        '-c:a', f"pcm_s{args.size}le",
        '-f', 'wav', args.audiostream,
    ]

    p = subprocess.run(cmd)
    if p.returncode:
        logging.error(f"FFMPEG returned non-zero return code: {p.returncode}")
        exit(1)
    logging.info("Processing successful")


if __name__ == "__main__":
    main()