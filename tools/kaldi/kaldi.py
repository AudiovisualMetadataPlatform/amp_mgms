#!/usr/bin/env python3

import os.path
import shutil
import subprocess
import sys
import tempfile
import argparse
import logging
from pathlib import Path
import math
import atexit
import os
import time

# The run_kaldi.sh script is assumed to be in a directory called kaldi-pua-apptainer, which is a peer to the
# galaxy install.  It can either be a check out of that repo, or just the script and the appropriate .sif file.
# by default the cwd is somewhere near: 
#    galaxy/database/jobs_directory/000/4/working


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", default=False, action="store_true", help="Turn on debugging")
    parser.add_argument("input_audio", help="Input audio file")
    parser.add_argument("kaldi_transcript_json", help="Output Kaldi Transcript JSON file")
    parser.add_argument("kaldi_transcript_text", help="Output Kaldi Transcript Text file")
    parser.add_argument("--gpu", default=False, action="store_true", help="Use GPU kaldi")
    parser.add_argument("--shell", default=False, action="store_true", help="Start a shell in the container after processing")
    args = parser.parse_args()    
    logging.basicConfig(format="%(asctime)s [%(levelname)-8s] (%(filename)s:%(lineno)d:%(process)d)  %(message)s", level=logging.DEBUG if args.debug else logging.INFO)   
    logging.info(f"Starting with args {args}")

    # copy the input file to a temporary directory
    with tempfile.TemporaryDirectory() as tmpdir:     
        logging.debug(f"Temporary directory: {tmpdir}")   
        # find the right Kaldi SIF and set up things to make it work...
        sif = Path(sys.path[0], f"kaldi-pua-{'gpu' if args.gpu else 'cpu'}.sif")
        if not sif.exists():
            logging.error(f"Kaldi SIF file {sif!s} doesn't exist!")
            exit(1)

        # create the necessary structure
        for d in ('input', 'output', 'temp'):
            os.mkdir(f"{tmpdir}/{d}")

        # put the shell sentinel into the container
        if args.shell:
            with open(f"{tmpdir}/temp/.start_shell", "w") as f:
                f.write("Start a shell after processing!")

        # put the debug sentinel into the container
        if args.debug:
            with open(f"{tmpdir}/temp/.debug", "w") as f:
                f.write("Debugging should be enabled within the container")

        # copy our input file
        shutil.copy(args.input_audio, f"{tmpdir}/input/xxx.wav")

        # build the apptainer command line
        cmd = ['apptainer', 'run', '-B', f"{tmpdir}:/writable", str(sif) ]
        logging.debug(f"Apptainer Command: {cmd}")
        if args.debug:
            p = subprocess.run(cmd, encoding='utf-8')        
        else:
            p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding='utf-8')        
        if p.returncode != 0:
            logging.error("KALDI failed")
            logging.error(p.stdout)
            exit(1)
        copy_failed = False
        for src, dst in ((f"{tmpdir}/output/xxx.txt", args.kaldi_transcript_text),
                         (f"{tmpdir}/output/xxx.json", args.kaldi_transcript_json)):
            try:                
                shutil.copy(src, dst)
            except Exception as e:
                logging.exception(f'Cannot copy {src} to {dst}')     
                copy_failed = True
        if copy_failed:
            logging.error("Kaldi didn't actually produce the files on a 'successful' run")
            logging.error(f"Kaldi's output:\n{p.stdout}")
            logging.error("contents of output: " + str(os.listdir(f"{tmpdir}/output")))

    logging.info(f"Finished running Kaldi with output {args.kaldi_transcript_json} and {args.kaldi_transcript_text}")
    exit(0 if not copy_failed else 1)


if __name__ == "__main__":
    main()
