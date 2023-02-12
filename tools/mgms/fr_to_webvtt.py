#!/usr/bin/env python3

import json
import argparse
import logging

from amp.schema.facial_recognition import FaceRecognition
#import amp.logger
import amp.vtt_helper


def main():    
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", default=False, action="store_true", help="Turn on debugging")
    parser.add_argument("amp_faces")
    parser.add_argument("web_vtt")
    args = parser.parse_args()
    logging.info(f"Starting with args {args}")
    (amp_faces, web_vtt) = (args.amp_faces, args.web_vtt)

    # Open the input file and create the fr object
    with open(amp_faces, 'r') as file:
        fr = FaceRecognition.from_json(json.load(file))

    # write header to output vtt file
    vtt_file = open(web_vtt, "w")
    vtt_file.write(amp.vtt_helper.get_header())
    
    # calculate frame duration
    duration = 1/fr.media.frameRate
    
    # Write the vtt lines    
    for f in fr.frames:
        vtt_file.write(amp.vtt_helper.get_empty_line())        
        # there is no end time for the face frames, use the frame duration to calculate it
        vtt_file.write(amp.vtt_helper.get_time(f.start, f.start + duration))
        vtt_file.write(amp.vtt_helper.get_line(None, f.objects[0].name))
    
    vtt_file.close()
    logging.info("Finished.")

if __name__ == "__main__":
    main()
