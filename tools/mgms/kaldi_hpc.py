#!/usr/bin/env python3

import argparse
from datetime import datetime
from pathlib import Path
import sys
import logging

import amp.logger
import amp.utils
import hpc_submit
import kaldi_transcript_to_amp_transcript

def main():
    """
    Submit a job to run ina speech segmenter on HPC
    """
    parser = argparse.ArgumentParser(description=main.__doc__)
    parser.add_argument("--debug", default=False, action="store_true", help="Turn on debugging")
#     parser.add_argument("root_dir", help="Galaxy root directory")
    parser.add_argument("input", help="input audio file")
    parser.add_argument("kaldi_transcript_json", help="Kaldi JSON output")
    parser.add_argument("kaldi_transcript_txt", help="Kalid TXT output")
    parser.add_argument("amp_transcript_json", help="AMP JSON output")
    parser.add_argument("hpc_timestamps", help="HPC Timestamps output")
    args = parser.parse_args()

    # get hpc dropbox dir path
    dropbox = amp.utils.get_work_dir("hpc_dropbox")
                                    
    # set up logging
#     logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO,
#                         stream=sys.stderr,
#                         format="%(asctime)s %(levelname)s %(message)s")
    
    # job parameters    
    logging.debug("Preparing kaldi HPC job")    
    job = {
        'script': 'kaldi',
        'input_map': {
            'input': args.input
        },
        'output_map': {
            'kaldi_json': args.kaldi_transcript_json,
            'kaldi_txt': args.kaldi_transcript_txt,
            'amp_json': args.amp_transcript_json
        }
    }

    logging.info("Submitting HPC job")
    job = hpc_submit.submit_and_wait(dropbox, job)

    logging.info("HPC job completed with status: " + job['job']['status'])
    if job['job']['status'] != 'ok':
        exit(1)
        
    logging.info("Convering output to AMP Transcript JSON")
    kaldi_transcript_to_amp_transcript.convert(args.input, args.kaldi_transcript_json, args.kaldi_transcript_txt, args.amp_transcript_json)
    
    logging.info("Job output:")
    logging.info(job)

    # Write the hpc timestamps output
    if "start" in job['job'].keys() and "end" in job['job'].keys():
        ts_output = {
            "start_time": job['job']["start"],
            "end_time": job['job']["end"],
            "elapsed_time": (datetime.strptime(job['job']["end"], '%Y-%m-%d %H:%M:%S.%f') - datetime.strptime(job['job']["start"], '%Y-%m-%d %H:%M:%S.%f')).total_seconds() 
        }
        amp.utils.write_json_file(ts_output, args.hpc_timestamps)

    exit(0)

if __name__ == "__main__":
    main()