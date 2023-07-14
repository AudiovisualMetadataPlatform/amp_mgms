#!/usr/bin/env amp_python.sif

# Merge multiple annotation files into a single file

import argparse
import logging
import amp.logging
from amp.annotations import Annotations
from pathlib import Path

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", default=False, action="store_true", help="Turn on debugging")
    parser.add_argument("annotation_in", nargs="+", help="Annotation files to merge")
    parser.add_argument("annotation_out", help="Updated Annotation file")
    args = parser.parse_args()
    amp.logging.setup_logging("merge_annotations", args.debug)
    logging.info(f"Starting with args {args}")

    # There should always be a valid annotation_in so the args below (except for the first) are ignored
    annotations = Annotations(args.annotation_in.pop(0), load_only=True)

    for a in args.annotation_in:
        if Path(a).exists():            
            logging.info(f"Merging file {a}")
            other = Annotations(a, load_only=True)
            annotations.merge(other)

    annotations.save(args.annotation_out)
    logging.info("Finished!")
    
    
if __name__ == "__main__":
    main()