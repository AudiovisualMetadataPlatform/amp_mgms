#!/usr/bin/env python3

import os.path
import shutil
import subprocess
import sys
import tempfile
import argparse

import amp.utils

# The run_kaldi.sh script is assumed to be in a directory called kaldi-pua-singularity, which is a peer to the
# galaxy install.  It can either be a check out of that repo, or just the script and the appropriate .sif file.
# by default the cwd is somewhere near: 
#    galaxy/database/jobs_directory/000/4/working
MODE = "cpu"

def main():
    #(root_dir, input_file, json_file, text_file) = sys.argv[1:5]
    parser = argparse.ArgumentParser()
    parser.add_argument("input_file")
    parser.add_argument("json_file")
    parser.add_argument("text_file")
    args = parser.parse_args()
    print(os.getcwd())
    # copy the input file to a temporary directory
    with tempfile.TemporaryDirectory() as tmpdir:
        shutil.copy(args.input_file, f"{tmpdir}/xxx.wav")
        
        #script = amp.utils.get_sif_dir(root_dir) + "/run_kaldi.sh"
        script = sys.path[0] + "/run_kaldi.sh"
        subprocess.run([script, MODE, tmpdir], check=True)
        # assuming the local kaldi ran, it's time to 
        # find our output files and copy them 
        print(os.listdir(tmpdir))
        print(os.listdir(f"{tmpdir}/transcripts/txt"))
        
        shutil.copy(f"{tmpdir}/transcripts/txt/xxx_16kHz.txt", amp.text_file)
        shutil.copy(f"{tmpdir}/transcripts/json/xxx_16kHz.json", amp.json_file)
        print(os.listdir(os.path.dirname(amp.json_file)))
        print(os.listdir(os.path.dirname(amp.text_file)))
    exit(0)

if __name__ == "__main__":
    main()
