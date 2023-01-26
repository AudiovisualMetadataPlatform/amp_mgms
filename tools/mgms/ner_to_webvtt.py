#!/usr/bin/env python3

import json
import argparse
import logging

from amp.schema.entity_extraction import EntityExtraction
#import amp.logger
import amp.vtt_helper


def main():    
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", default=False, action="store_true", help="Turn on debugging")
    parser.add_argument("amp_entities")
    parser.add_argument("web_vtt")
    args = parser.parse_args()
    logging.info(f"Starting with args {args}")
    (amp_entities, web_vtt) = (args.amp_entities, args.web_vtt)

    # Open the input file and create the ner object
    with open(amp_entities, 'r') as file:
        ner = EntityExtraction.from_json(json.load(file))

    # write header to output vtt file
    vtt_file = open(web_vtt, "w")
    vtt_file.write(amp.vtt_helper.get_header())
    
    # Write the vtt lines
    for e in ner.entities:
        vtt_file.write(amp.vtt_helper.get_empty_line())        
        vtt_file.write(amp.vtt_helper.get_time(e.start, e.end))
        vtt_file.write(amp.vtt_helper.get_line(None, e.text))
    
    vtt_file.close()
    logging.info("Finished.")

if __name__ == "__main__":
    main()
