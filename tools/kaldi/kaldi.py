#!/usr/bin/env python3

import os.path
import shutil
import subprocess
import sys
import tempfile
import argparse
import logging
from pathlib import Path

import amp.utils
import amp.logger


# The run_kaldi.sh script is assumed to be in a directory called kaldi-pua-singularity, which is a peer to the
# galaxy install.  It can either be a check out of that repo, or just the script and the appropriate .sif file.
# by default the cwd is somewhere near: 
#    galaxy/database/jobs_directory/000/4/working


def main():
    #(root_dir, input_file, json_file, text_file) = sys.argv[1:5]
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", default=False, action="store_true", help="Turn on debugging")
    parser.add_argument("input_file")
    parser.add_argument("json_file")
    parser.add_argument("text_file")
    parser.add_argument("--gpu", default=False, action="store_true", help="Use GPU kaldi")
    args = parser.parse_args()
    logging.info(f"Starting with args {args}")

    # copy the input file to a temporary directory
    with tempfile.TemporaryDirectory() as tmpdir:
        shutil.copy(args.input_file, f"{tmpdir}/xxx.wav")
        tmp = Path(tmpdir)
        # find the right Kaldi SIF and set up things to make it work...
        sif = Path(sys.path[0], f"kaldi-pua-{'gpu' if args.gpu else 'cpu'}.sif")
        if not sif.exists():
            logging.error(f"Kaldi SIF file {sif!s} doesn't exist!")
            exit(1)

        # build the singularity command line
        cmd = ['singularity', 'run', '-B', f"{tmpdir}:/audio_in", '--writable-tmpfs', str(sif) ]
        logging.debug(f"Singularity Command: {cmd}")
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding='utf-8')
        if p.returncode != 0:
            logging.error("KALDI failed")
            logging.error(p.stdout)
            exit(1)
        shutil.copy(f"{tmpdir}/transcripts/txt/xxx_16kHz.txt", args.text_file)
        shutil.copy(f"{tmpdir}/transcripts/json/xxx_16kHz.json", args.json_file)
    logging.info("Finished")
    exit(0)

if __name__ == "__main__":
    main()
