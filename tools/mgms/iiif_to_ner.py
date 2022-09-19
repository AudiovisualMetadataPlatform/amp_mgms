#!/usr/bin/env amp_python.sif

import json
import sys
import traceback
import argparse
import logging

import amp.logging
import amp.utils
from amp.schema.entity_extraction import EntityExtraction, EntityExtractionMedia, EntityExtractionEntity, EntityExtractionEntityScore


# Convert IIIF manifest JSON file to standard NER output JSON file.
# Usage: iiif_to_ner.py root_dir from_iiif original_ner to_ner
def main():
    # parse command line arguments
    #root_dir = sys.argv[1]
    #from_iiif = sys.argv[2]     # json file output from HMGM NER editor in IIIF format to convert from
    #original_ner = sys.argv[3]  # json file originally generated by previous NER tool in standard AMP NER format
    #to_ner = sys.argv[4]        # json file fed to downstream MGMs in standard AMP NER format to convert to
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", default=False, action="store_true", help="Turn on debugging")
    parser.add_argument("from_iiif", help="json file output from HMGM NER editor in IIIF format to convert from")
    parser.add_argument("original_ner", help="json file originally generated by previous NER tool in standard AMP NER format")
    parser.add_argument("to_ner", help="json file fed to downstream MGMs in standard AMP NER format to convert to")
    args = parser.parse_args()
    amp.logging.setup_logging("iiif_to_ner", args.debug)
    logging.debug(f"Starting with args {args}")
    (from_iiif, original_ner, to_ner) = (args.from_iiif, args.original_ner, args.to_ner)

    # using output instead of input filename as the latter is unique while the former could be used by multiple jobs 

    try:
        # if from_iiif is in error raise exception to notify HMGM job runner to fail the job
        # otherwise if from_iiif doesn't exist yet, exit to requeue and keep waiting
        amp.utils.exit_if_file_not_ready(from_iiif)
        logging.info(f"Converting from IIIF {from_iiif} to NER {to_ner}")

        # parse output IIIF and original input NER
        with open(from_iiif, 'r') as iiif_file:
            iiif_data = json.load(iiif_file)
        with open(original_ner, 'r') as ner_file:
            ner_data = json.load(ner_file)
    
        # update entities in original input NER
        entity_dict = build_ner_entity_dictionary(ner_data)
        ner_data["entities"] = generate_ner_entities(iiif_data, entity_dict)
    
        # write entities back to output NER
        with open(to_ner, "w") as outfile: 
            json.dump(ner_data, outfile) 
        
        logging.info(f"Successfully converted from IIIF {from_iiif} to NER {to_ner}")
        sys.stdout.flush()
        # as the last command in HMGM, implicitly exit 0 here to let the whole job complete in success
    except Exception as e:
        # as the last command in HMGM, exit 1 to let the whole job fail
        logging.exception(f"Failed to convert from IIIF {from_iiif} to NER {to_ner}")
        exit(1)            


# Build a dictionary for NER entities with start time as key and entity as value, to allow efficient searching of entity by timestamp.
# Note: Matching IIIF annoation with NER entity by timestamp is based on the assumption that timestamp can not be changed by NER editor,
# (it can be added/deleted), and at any given time there can be only one entity; thus timestamp can uniquely identify an entity in both IIIF and NER.
def build_ner_entity_dictionary(ner_data):
    entity_dict = {}

    # create a {start, entity} tuple for each entity in ner_data 
    for entity in ner_data["entities"]:
        entity_dict[entity["start"]] = entity

    return entity_dict


# Generate NER entities using the given iiif_data and entity_dict
def generate_ner_entities(iiif_data, entity_dict):
    entities = []

    # update/create an NER entity for each IIIF annotation in iiif_data;
    for annotation in iiif_data["annotations"][0]["items"]:        
        time = annotation["target"]["selector"]["t"]
        if time in entity_dict:
            # if the annotation timestamp matches an entity start time, update the entity text/type with that from the annotation
            entity = entity_dict[time]
            entity["type"] = annotation["body"]["value"]
            entity["text"] = annotation["label"]["en"][0]
            # start, score and other fields in entity remain the same
        else:
            # otherwise create a new entity using fields in the annotation and with a full score    
            entity = {
                "type": annotation["body"]["value"],
                "text": annotation["label"]["en"][0],
                "start": time,
                "score": {
                    "type": "relevance",
                    "value": 1.0
                }
            }
        entities.append(entity)

    # those in original NER but not in IIIF (i.e. deleted by NER editor) are excluded from the entity list
    return entities


if __name__ == "__main__":
    main()    
