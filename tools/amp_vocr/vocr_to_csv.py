#!/usr/bin/env python3
import argparse
import sys
import json

from video_ocr import VideoOcr


def main():
    #(amp_vocr, amp_vocr_csv) = sys.argv[1:3]
    parser = argparse.ArgumentParser()
    parser.add_argument("amp_vocr", help="AMP Video OCR")
    parser.add_argument("amp_vocr_csv", help="CSV output file")
    args = parser.parse_args()
    (amp_vocr, amp_vocr_csv) = (args.amp_vocr, args.amp_vocr_csv)


    # Open the file and create the vocr object
    with open(amp_vocr, 'r') as file:
        vocr = VideoOcr.from_json(json.load(file))

    # Write the csv file
    vocr.toCsv(amp_vocr_csv)


if __name__ == "__main__":
    main()
