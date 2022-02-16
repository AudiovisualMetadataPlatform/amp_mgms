#!/usr/bin/env mgm_python.sif

import sys
import os
import json
import argparse

from amp.schema.contact_sheet import ContactSheet
import logging
import amp.logger

def main():

	#print(sys.argv)
	number_of_columns = 4
	photow = 300
	margin = 10
	padding = 3

	#input_file = sys.argv[1]
	#context_json = sys.argv[2]
	#amp_contact_sheets = sys.argv[3]
	parser = argparse.ArgumentParser()
	parser.add_argument("--debug", default=False, action="store_true", help="Turn on debugging")
	parser.add_argument("input_file", help="INput file")
	parser.add_argument("context_json", help="JSON context")
	parser.add_argument("amp_contact_sheets", help="AMP Contact sheets")
	args = parser.parse_args()
	logging.info(f"Starting with args {args}")
	(input_file, context_json, amp_contact_sheets) = (args.input_file, args.context_json, args.amp_context_sheets)


	context = json.loads(context_json)
	collection_id = context["collectionId"]
	
	c = ContactSheet(input_file, amp_contact_sheets, number_of_columns, photow, margin, padding)

	video_length_seconds = c.get_length(input_file)
	logging.debug("Collection: " + collection_id)
	logging.debug("Duration: " + str(video_length_seconds))
	if int(collection_id) in (3, 4):
		if video_length_seconds < 2000:
			logging.info("Creating a frame per 20 seconds")
			c.create_time(20)
		else:
			logging.info("Creating a frame every 1%: " + str(video_length_seconds * .01) + " seconds")
			c.create_time(int(video_length_seconds * .01))
	else:
		if video_length_seconds < 300:
			logging.info("Creating a frame per 10 seconds")
			c.create_time(10)
		elif video_length_seconds < 1800:
			logging.info("Creating a frame per 60 seconds")
			c.create_time(60)
		else:
			logging.info("Creating a frame per 120 seconds")
			c.create_time(120)
	logging.info("Finished.")


if __name__ == "__main__":
	main()
