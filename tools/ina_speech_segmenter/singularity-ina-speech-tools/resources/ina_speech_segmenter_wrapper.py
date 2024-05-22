#!/usr/bin/env python3

import sys
import json
import os
import subprocess

from segmentation import Segmentation
from inaSpeechSegmenter import Segmenter

def main():
    (input_file, json_file) = sys.argv[1:3]
    
    # Run ina_speech_segmenter on input file
    # the result is a list of tuples
    # each tuple contains:
    # * label in 'Male', 'Female', 'Music', 'NOACTIVITY'
    # * start time of the segment
    # * end time of the segment
    seg = Segmenter()
    segmentation = seg(input_file)

    # Convert the resulting list of tuples to an object for serialization
    seg_schema = convert_to_segmentation_schema(input_file, segmentation)

    # Serialize the json and write it to destination file
    write_output_json(seg_schema, json_file)
    exit(0)

def convert_to_segmentation_schema(filename, segmentation):
    # Create a segmentation object to serialize
    seg_schema = Segmentation()
    seg_schema.media.filename = filename

    # For each segment returned by the ina_speech_segmenter, add 
    # a corresponding segment formatted to json spec
    for segment in segmentation:
        seg_schema.addSegment(segment[0], segment[0], float(segment[1]), float(segment[2]))

    return seg_schema


# Serialize schema obj and write it to output file
def write_output_json(seg_schema, json_file):
    # Serialize the segmentation object
    with open(json_file, 'w') as outfile:
        json.dump(seg_schema, outfile, default=lambda x: x.__dict__)

if __name__ == "__main__":
    if "INASPEECH_OLDPWD" in os.environ:
         os.chdir(os.environ["INASPEECH_OLDPWD"])
    main()
