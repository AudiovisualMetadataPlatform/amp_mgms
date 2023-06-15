#!/usr/bin/env amp_python.sif

import argparse
import logging

import amp.logging
from amp.schema.contact_sheet import ContactSheet
from amp.fileutils import read_json_file

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", default=False, action="store_true", help="Turn on debugging")
    parser.add_argument("input_video", help="Input video file")
    parser.add_argument("mode", choices=['vocr', 'faces', 'shot'], help="contact sheet mode")
    parser.add_argument("amp_input", help="Input AMP file")
    parser.add_argument("contact_sheet", help="Output Contact Sheet file")
    parser.add_argument('--columns', type=int, default=4, help="Number of thumbnail columns of per row")
    parser.add_argument('--width', type=int, default=300, help="Width of thumbnail image")
    parser.add_argument('--margin', type=int, default=10, help="Margin around each thumbnail")
    parser.add_argument('--padding', type=int, default=3, help="Padding around each thumbnail")
    args = parser.parse_args()
    amp.logging.setup_logging("contact_sheet", args.debug)
    logging.info(f"Starting with args {args}")
    sheet = ContactSheet(args.input_video, args.contact_sheet, args.columns, args.width, args.margin, args.padding)
    data = read_json_file(args.amp_input)
    if args.mode == "vocr":
        sheet.create_vocr(data)
    elif args.mode == "faces":
        sheet.create_faces(data)
    elif args.mode == "shot":
        sheet.create_shots(data)
    logging.info("Finished.")


if __name__ == "__main__":
	main()