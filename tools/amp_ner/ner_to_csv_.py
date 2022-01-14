#!/usr/bin/env python3

import sys
import json
import argparse

from entity_extraction import EntityExtraction

def main():    
    #(amp_entities, amp_entities_csv) = sys.argv[1:3]
    parser = argparse.ArgumentParser()
    parser.add_argument("amp_entities")
    parser.add_argument("amp_entities_csv")
    args = parser.parse_args()
    (amp_entities, amp_entities_csv) = (args.amp_entities, args.amp_entities_csv)

    # Open the file and create the ner object
    with open(amp_entities, 'r') as file:
        ner = EntityExtraction.from_json(json.load(file))

    # Write the csv file
    ner.toCsv(amp_entities_csv)


if __name__ == "__main__":
    main()
