#!/bin/env amp_python.sif
#
# Simple script that doesn't use any non-standard library
# modules or any executables that aren't part of a 
# system base install.
#
# All this does is produce a text file that contains the name/size of the input file.

import argparse
import logging
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="Return basic information about a file")
    parser.add_argument('--debug', default=False, action='store_true', help="Turn on debugging")    
    parser.add_argument('input', help="Input filename")
    parser.add_argument('output', help="Output filename without extension")
    args = parser.parse_args()
    logging.basicConfig(format="%(asctime)s [%(levelname)-8s] (%(filename)s:%(lineno)d)  %(message)s",
                        level=logging.DEBUG if args.debug else logging.INFO)
    logging.debug(f"input={args.input}, output={args.output}")
    infile = Path(args.input)
    with open(args.output, "w") as f:
        f.write(f"{infile.stem} = {infile.stat().st_size}\n")
    logging.info(f"Wrote file {args.output}")


if __name__ == "__main__":
    main()