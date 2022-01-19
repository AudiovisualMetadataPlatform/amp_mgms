#!/usr/bin/env python3

import os
import os.path
import shutil
import subprocess
import sys
import tempfile
import argparse

import amp.utils


def main():
    #(root_dir, input_audio, min_segment_duration, amp_segments) = sys.argv[1:5]
    parser = argparse.ArgumentParser()
    parser.add_argument("root_dir")
    parser.add_argument("input_audio")
    parser.add_argument("min_segment_duration")
    parser.add_argument("amp_segments")
    args = parser.parse_args()
    (root_dir, input_audio, min_segment_duration, amp_segments) = (args.root_dir, args.input_audio, args.min_segment_duration, args.amp_segments)
    
    
    print("Current directory: " + os.getcwd())
    print("Input audio: " + input_audio)
    
    # use a tmp directory accessible to the singularity for input/output
    with tempfile.TemporaryDirectory(dir = "/tmp") as tmpdir:
        # copy the input audio file to the tmp directory
        filename = os.path.basename(input_audio)
        shutil.copy(input_audio, f"{tmpdir}/{filename}")
        print("Temporary directory " + tmpdir + " after input file copied: " + str(os.listdir(tmpdir)))
        
        # The applause_detection singularity file is assumed to be @ {mgm_sif}/applause_detection.sif
        #sif = amp.utils.get_sif_dir(root_dir) + "/applause_detection.sif"
        # the new build puts the sif next to the script.
        sif = sys.path[0] + "/applause_detection.sif"

        # run singularity
        subprocess.run([sif, tmpdir, min_segment_duration], check=True)

        # copy the corresponding temporary output file to the output AMP segments JSON
        print("Temporary directory " + tmpdir + " after output file generated: " + str(os.listdir(tmpdir)))   
        shutil.copy(f"{tmpdir}/{filename}.json", amp_segments)
        print("Output AMP Segment: " + amp_segments)
    exit(0)

if __name__ == "__main__":
    main()