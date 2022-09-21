#!/usr/bin/env amp_python.sif

import spacy
import argparse

import amp.nerutils
import amp.logging
import logging
from amp.fileutils import write_json_file

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", default=False, action="store_true", help="Turn on debugging")
    parser.add_argument("amp_transcript", help="Input Transcript")
    parser.add_argument("spacy_entities", help="Output spacy entities")
    parser.add_argument("amp_entities", help="Output amp entities")
    parser.add_argument("--ignore_types", type=str, default="QUANTITY", help="NER types to ignore")
    args = parser.parse_args()
    amp.logging.setup_logging("spacy_ner", args.debug)
    logging.info(f"Starting args={args}")

    # preprocess NER inputs and initialize AMP entities output
    [amp_transcript_obj, amp_entities_obj, ignore_types_list] = amp.nerutils.initialize_amp_entities(args.amp_transcript, args.amp_entities, args.ignore_types)

    # if we reach here, further processing is needed, continue with Spacy   
     
    # load English tokenizer, tagger, parser, NER and word vectors
    nlp = spacy.load("en_core_web_lg")
    
    # run Spacy with input transcript
    spacy_entities_obj = nlp(amp_transcript_obj.results.transcript)

    # write the output Spacy entities object to JSON file
    write_json_file(spacy_entities_obj.to_json(), args.spacy_entities)
    
    # populate AMP Entities list based on input AMP transcript words list and output AWS Entities list  
    amp.nerutils.populate_amp_entities(amp_transcript_obj, spacy_entities_obj.ents, amp_entities_obj, ignore_types_list)

    # write the output AMP entities object to JSON file
    write_json_file(amp_entities_obj, args.amp_entities)
    logging.info("Finished")

if __name__ == "__main__":
    main()
