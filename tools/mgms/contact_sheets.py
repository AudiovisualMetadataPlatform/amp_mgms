#!/usr/bin/env mgm_python.sif

import ffmpeg
import sys
import requests
import logging
import json
from amp.schema.contact_sheet import ContactSheet
import logging
import amp.logger
import argparse


def main():
	#label = "AMP Contact Sheets " + datetime.today().strftime("%b %d %Y %H:%M:%S")
	# TODO:  use argparse.  The parameters are a mess.
	if True:
		parser = argparse.ArgumentParser()
		parser.add_argument("--debug", default=False, action="store_true", help="Turn on debugging")
		parser.add_argument("input_file", help="Source file")
		parser.add_argument("type", choices=['time', 'quantity', 'shot', 'facial'], help="sheet type")
		parser.add_argument("--frame_seconds", type=int, default=0, help="seconds per frame")
		parser.add_argument("--frame_quantity", type=int, default=0, help="frame quantity")
		parser.add_argument("--amp_shots", default='', help="AMP shots file")
		parser.add_argument("--amp_facial_recognition", default='', help="AMP Facial recognition file")
		parser.add_argument("--amp_contact_sheets", default='', help="AMP Contact sheets")
		parser.add_argument('--number_of_columns', type=int, default=4, help="Number of columns")
		parser.add_argument('--photow', type=int, default=300, help="Photo width")
		parser.add_argument('--margin', type=int, default=10, help="Margin")
		parser.add_argument('--padding', type=int, default=3, help="Padding")
		args = parser.parse_args()
		logging.info(f"Starting with args {args}")
		(input_file, type, frame_seconds, frame_quantity, amp_shots, amp_facial_recognition,
		 amp_contact_sheets, number_of_columns, photow, margin, padding) = (args.input_file, args.type, args.frame_seconds, args.frame_quantity, args.amp_shots, args.amp_facial_recognition,
		 args.amp_contact_sheets, args.number_of_columns, args.photow, args.margin, args.padding)
	else:
		print(sys.argv)
		input_file = sys.argv[1]
		type = sys.argv[2]
		frame_seconds = 0
		if sys.argv[3] != '':
			frame_seconds = int(sys.argv[3])
		frame_quantity = 0
		if sys.argv[4] != '':
			frame_quantity = int(sys.argv[4])
		amp_shots = sys.argv[5]
		amp_facial_recognition = sys.argv[6]
		amp_contact_sheets = sys.argv[7]

		number_of_columns = 4
		photow = 300
		margin = 10
		padding = 3

		if sys.argv[8] != '':
			number_of_columns = int(sys.argv[8])
		if sys.argv[9] != '':
			photow = int(sys.argv[9])
		if sys.argv[10] != '':
			margin = int(sys.argv[10])
		if sys.argv[11] != '':
			padding = int(sys.argv[11])

	# Print for debugging purposes
	logging.debug("Input File: " + input_file)
	logging.debug("type: " + type)
	logging.debug("frame_seconds: " + str(frame_seconds))
	logging.debug("frame_quantity: " + str(frame_quantity))
	logging.debug("amp_shots: " + amp_shots)
	logging.debug("amp_facial_recognition: " + amp_facial_recognition)
	logging.debug("Output File: " + amp_contact_sheets)
	logging.debug("Number of Columns: " + str(number_of_columns))
	logging.debug("Photo Width: " + str(photow))
	logging.debug("Margin: " + str(margin))
	logging.debug("Padding: " + str(padding))

	# Initialize the contact sheet
	c = ContactSheet(input_file, amp_contact_sheets, number_of_columns, photow, margin, padding)

	# Based on input, create the contact sheet
	if type == 'time':
		c.create_time(frame_seconds)
	elif type == 'quantity':
		c.create_quantity(frame_quantity)
	elif type == 'shot':
		shots = read_json_file(amp_shots)
		c.create_shots(shots)
	elif type == 'facial':
		fr = read_json_file(amp_facial_recognition)
		c.create_facial(fr)
	logging.info("Finished.")

def read_json_file(input):
	with open(input) as f:
		data = json.load(f)
		return data

if __name__ == "__main__":
	main()
