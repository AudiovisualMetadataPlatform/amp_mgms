#!/usr/bin/env amp_python.sif

import argparse
from datetime import datetime
import csv
from pathlib import Path
import sys
import logging

import amp.logger
import amp.utils
import hpc_submit

from segmentation import Segmentation, SegmentationMedia


def main():
    """
    Submit a job to run ina speech segmenter on HPC
    """
    parser = argparse.ArgumentParser(description=main.__doc__)
    parser.add_argument("--debug", default=False, action="store_true", help="Turn on debugging")
#     parser.add_argument("root_dir", help="Galaxy root directory")
    parser.add_argument("input", help="input audio file")
    parser.add_argument("segments", help="INA Speech Segmenter output")
    parser.add_argument("amp_segments", help="AMP Segmentation Schema output")
    parser.add_argument("hpc_timestamps", help="HPC Timestamps output")
    args = parser.parse_args()

    # set up logging
#     logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO,
#                         stream=sys.stderr,
#                         format="%(asctime)s %(levelname)s %(message)s")
    
    # get hpc dropbox dir path
    dropbox = amp.utils.get_work_dir("hpc_dropbox")
    
    # job parameters    
    job = {
        'script': 'ina_speech_segmenter',
        'input_map': {
            'input': args.input
        },
        'output_map': {
            'segments': args.segments
        }
    }
    
    logging.info("Submitting job to HPC")
    job = hpc_submit.submit_and_wait(dropbox, job)

    logging.info("Checking job status: " + job['job']['status'])
    if job['job']['status'] != 'ok':
        exit(1)

    logging.info("Reading TSV into list of tuples")
    with open(args.segments, 'r') as csvin:
        data=[tuple(line) for line in csv.reader(csvin, delimiter='\t')]

     # Convert the resulting list of tuples to an object for serialization
    logging.info("Converting ina output  to segmentation schema")
    seg_schema = convert_to_segmentation_schema(args.input, data)

    # Serialize the json and write it to destination file
    logging.info("Writing output json")
    amp.utils.write_json_file(seg_schema, args.amp_segments)

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


def convert_to_segmentation_schema(filename, segmentation):
    media = SegmentationMedia()
    media.filename = filename
    # Create a segmentation object to serialize
    seg_schema = Segmentation(media = media)

    # For each segment returned by the ina_speech_segmenter, add 
    # a corresponding segment formatted to json spec
    row = 0
    for segment in segmentation:
        row+=1
        if row == 1:
            continue
        seg_schema.addSegment(segment[0], segment[0], float(segment[1]), float(segment[2]))
    return seg_schema


if __name__ == "__main__":
    main()