#!/usr/bin/env amp_python.sif

import json
import argparse
from amp.schema.entity_extraction import EntityExtraction
import logging
import amp.logging

def main():        
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", default=False, action="store_true", help="Turn on debugging")
    parser.add_argument("amp_entities")
    parser.add_argument("amp_entities_csv")
    args = parser.parse_args()
    amp.logging.setup_logging("ner_to_csv", args.debug)
    logging.info(f"Starting with args {args}")

    # Open the file and create the ner object
    ner = EntityExtraction(read_json_file(args.amp_entities))
    
    # Write the csv file
    ner.toCsv(args.amp_entities_csv)
    logging.info("Finished.")

if __name__ == "__main__":
    main()
