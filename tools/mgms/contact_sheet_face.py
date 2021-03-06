#!/usr/bin/env mgm_python.sif

import sys
import os
import json
import argparse
import logging

import amp.logger
import amp.utils
from amp.schema.contact_sheet import ContactSheet


def main():
	parser = argparse.ArgumentParser()
	parser.add_argument("--debug", default=False, action="store_true", help="Turn on debugging")
	parser.add_argument("input_video", help="Input video file")
	parser.add_argument("amp_faces", help="Input AMP Faces file")
	parser.add_argument("contact_sheet", help="Output Contact Sheet file")
	parser.add_argument('--columns', type=int, default=4, help="Number of thumbnail columns of per row")
	parser.add_argument('--width', type=int, default=300, help="Width of thumbnail image")
	parser.add_argument('--margin', type=int, default=10, help="Margin around each thumbnail")
	parser.add_argument('--padding', type=int, default=3, help="Padding around each thumbnail")
	args = parser.parse_args()
	
	logging.info(f"Starting with args {args}")
	(input_video, amp_faces, contact_sheet, columns, width, margin, padding) = (args.input_video, args.amp_faces, args.contact_sheet, args.columns, args.width, args.margin, args.padding)

	# Print for debugging purposes
	logging.debug("input_video: " + input_video)
	logging.debug("amp_faces: " + amp_faces)
	logging.debug("contact_sheet: " + contact_sheet)
	logging.debug("columns: " + str(columns))
	logging.debug("width: " + str(width))
	logging.debug("margin: " + str(margin))
	logging.debug("padding: " + str(padding))
	
	sheet = ContactSheet(input_video, contact_sheet, columns, width, margin, padding)
	faces = amp.utils.read_json_file(amp_faces)
	sheet.create_faces(faces)
	logging.info("Finished.")


if __name__ == "__main__":
	main()
