#!/usr/bin/env amp_python.sif
import argparse
import json

from amp.schema.video_ocr import VideoOcr
import logging
import amp.logging

def main():
    #(amp_vocr, amp_vocr_csv) = sys.argv[1:3]
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", default=False, action="store_true", help="Turn on debugging")
    parser.add_argument("amp_vocr", help="AMP Video OCR")
    parser.add_argument("amp_vocr_csv", help="CSV output file")
    args = parser.parse_args()
    amp.logging.setup_logging("vocr_to_csv", args.debug)
    logging.info(f"Starting with args {args}")
    (amp_vocr, amp_vocr_csv) = (args.amp_vocr, args.amp_vocr_csv)


    # Open the file and create the vocr object
    with open(amp_vocr, 'r') as file:
        vocr = VideoOcr.from_json(json.load(file))

    # Write the csv file
    vocr.toCsv(amp_vocr_csv)
    logging.info("Finished.")

if __name__ == "__main__":
    main()
