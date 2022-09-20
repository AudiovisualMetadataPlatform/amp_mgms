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
	parser.add_argument("amp_vocr", help="Input AMP VOCR file")
	parser.add_argument("contact_sheet", help="Output Contact Sheet file")
	parser.add_argument('--columns', type=int, default=4, help="Number of thumbnail columns of per row")
	parser.add_argument('--width', type=int, default=300, help="Width of thumbnail image")
	parser.add_argument('--margin', type=int, default=10, help="Margin around each thumbnail")
	parser.add_argument('--padding', type=int, default=3, help="Padding around each thumbnail")
	args = parser.parse_args()
	amp.logging.setup_logging("contact_sheet_vocr", args.debug)
	logging.info(f"Starting with args {args}")
	(input_video, amp_vocr, contact_sheet, columns, width, margin, padding) = (args.input_video, args.amp_vocr, args.contact_sheet, args.columns, args.width, args.margin, args.padding)

	# Print for debugging purposes
	logging.debug("input_video: " + input_video)
	logging.debug("amp_vocr: " + amp_vocr)
	logging.debug("contact_sheet: " + contact_sheet)
	logging.debug("columns: " + str(columns))
	logging.debug("width: " + str(width))
	logging.debug("margin: " + str(margin))
	logging.debug("padding: " + str(padding))
	
	sheet = ContactSheet(input_video, contact_sheet, columns, width, margin, padding)
	vocr = read_json_file(amp_vocr)
	sheet.create_vocr(vocr)
	logging.info("Finished.")


if __name__ == "__main__":
	main()
