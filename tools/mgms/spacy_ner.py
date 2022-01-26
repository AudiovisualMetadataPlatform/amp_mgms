#!/usr/bin/env mgm_python.sif


import spacy
import sys
import argparse

import amp.utils
import amp.ner_helper
import amp.logger
import logging

def main():
    #(amp_transcript, spacy_entities, amp_entities, ignore_types) = sys.argv[1:5]
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", default=False, action="store_true", help="Turn on debugging")
    parser.add_argument("amp_transcript")
    parser.add_argument("spacy_entities")
    parser.add_argument("amp_entities")
    parser.add_argument("ignore_types")
    args = parser.parse_args()
    logging.info(f"Starting args={args}")
    (amp_transcript, spacy_entities, amp_entities, ignore_types) = (args.amp_transcript, args.spacy_entities, args.amp_entities, args.ignore_types)

    # preprocess NER inputs and initialize AMP entities output
    [amp_transcript_obj, amp_entities_obj, ignore_types_list] = amp.ner_helper.initialize_amp_entities(amp_transcript, amp_entities, ignore_types)

    # if we reach here, further processing is needed, continue with Spacy   
     
    # load English tokenizer, tagger, parser, NER and word vectors
    nlp = spacy.load("en_core_web_lg")
    
    # run Spacy with input transcript
    spacy_entities_obj = nlp(amp_transcript_obj.results.transcript)

    # write the output Spacy entities object to JSON file
    amp.utils.write_json_file(spacy_entities_obj.to_json(), spacy_entities)
    
    # populate AMP Entities list based on input AMP transcript words list and output AWS Entities list  
    amp.ner_helper.populate_amp_entities(amp_transcript_obj, spacy_entities_obj.ents, amp_entities_obj, ignore_types_list)

    # write the output AMP entities object to JSON file
    amp.utils.write_json_file(amp_entities_obj, amp_entities)
    logging.info("Finished")

if __name__ == "__main__":
    main()
