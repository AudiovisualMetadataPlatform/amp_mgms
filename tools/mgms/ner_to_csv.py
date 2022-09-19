#!/usr/bin/env amp_python.sif

import sys
import json
import argparse

from amp.schema.entity_extraction import EntityExtraction
import logging
import amp.logging

def main():    
    #(amp_entities, amp_entities_csv) = sys.argv[1:3]
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", default=False, action="store_true", help="Turn on debugging")
    parser.add_argument("amp_entities")
    parser.add_argument("amp_entities_csv")
    args = parser.parse_args()
    amp.logging.setup_logging("ner_to_csv", args.debug)
    logging.info(f"Starting with args {args}")
    (amp_entities, amp_entities_csv) = (args.amp_entities, args.amp_entities_csv)

    # Open the file and create the ner object
    with open(amp_entities, 'r') as file:
        ner = EntityExtraction.from_json(json.load(file))

    # Write the csv file
    ner.toCsv(amp_entities_csv)
    logging.info("Finished.")

if __name__ == "__main__":
    main()
