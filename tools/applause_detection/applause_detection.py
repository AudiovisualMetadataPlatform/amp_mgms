#!/usr/bin/env python3

import os
import os.path
import shutil
import subprocess
import sys
import tempfile
import argparse
import logging

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", default=False, action="store_true", help="Turn on debugging")
    parser.add_argument("--min_segment_duration", type=int, default=1000)
    parser.add_argument("input_audio")    
    parser.add_argument("amp_segments")
    args = parser.parse_args()
    logging.basicConfig(format="%(asctime)s [%(levelname)-8s] (%(filename)s:%(lineno)d:%(process)d)  %(message)s", level=logging.DEBUG if args.debug else logging.INFO)    
    logging.info(f"Starting with args={args}")    

    # use a tmp directory accessible to the apptainer for input/output
    with tempfile.TemporaryDirectory() as tmpdir:
        # copy the input audio file to the tmp directory
        filename = os.path.basename(args.input_audio)
        shutil.copy(args.input_audio, f"{tmpdir}/{filename}")        
        
        # The applause_detection apptainer file is assumed to be next to the 
        # script.
        sif = sys.path[0] + "/applause_detection.sif"

        # run apptainer
        subprocess.run([sif, tmpdir, str(args.min_segment_duration)], check=True)

        # copy the corresponding temporary output file to the output AMP segments JSON        
        shutil.copy(f"{tmpdir}/{filename}.json", args.amp_segments)        
    logging.info("Finished")
    exit(0)

if __name__ == "__main__":
    main()
