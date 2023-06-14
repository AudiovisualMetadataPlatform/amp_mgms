#!/usr/bin/env python3

import json
import argparse
import logging

from amp.schema.entity_extraction import EntityExtraction
import amp.vtt_helper


def main():    
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", default=False, action="store_true", help="Turn on debugging")
    parser.add_argument("amp_entities")
    parser.add_argument("web_vtt")
    args = parser.parse_args()
    logging.info(f"Starting with args {args}")

    # Open the input file and create the ner object
    with open(args.amp_entities, 'r') as file:
        ner = EntityExtraction.from_json(json.load(file))

    # write header to output vtt file
    vtt_file = open(args.web_vtt, "w")
    vtt_file.write(amp.vtt_helper.get_header())
    
    # Write the vtt lines
    for e in ner.entities:
        vtt_file.write(amp.vtt_helper.get_empty_line())  
        # there is no end timestamp per entity. just set it same as start time, as the duration is likely very short      
        vtt_file.write(amp.vtt_helper.get_time(e.start, e.start))
        vtt_file.write(amp.vtt_helper.get_line(None, e.text))
    
    vtt_file.close()
    logging.info("Finished.")

if __name__ == "__main__":
    main()
