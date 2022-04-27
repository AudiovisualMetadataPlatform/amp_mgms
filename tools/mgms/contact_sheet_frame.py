#!/usr/bin/env mgm_python.sif

import sys
import os
import json
import argparse
import logging
import math

import amp.logger
import amp.utils
from amp.schema.contact_sheet import ContactSheet


def main():
	parser = argparse.ArgumentParser()
	parser.add_argument("--debug", default=False, action="store_true", help="Turn on debugging")
	parser.add_argument("input_video", help="Input video file")
	parser.add_argument("contact_sheet", help="Output Contact Sheet file")
	parser.add_argument("--frame_interval", type=int, default=0, help="Interval in seconds between frames")
	parser.add_argument("--frame_quantity", type=int, default=0, help="Total number of frames")	
	parser.add_argument('--columns', type=int, default=4, help="Number of thumbnail columns of per row")
	parser.add_argument('--width', type=int, default=300, help="Width of thumbnail image")
	parser.add_argument('--margin', type=int, default=10, help="Margin around each thumbnail")
	parser.add_argument('--padding', type=int, default=3, help="Padding around each thumbnail")
	args = parser.parse_args()
	
	logging.info(f"Starting with args {args}")
	(input_video, contact_sheet, frame_interval, frame_quantity, columns, width, margin, padding) = (args.input_video, args.contact_sheet, args.frame_interval, args.frame_quantity, args.columns, args.width, args.margin, args.padding)

	# Print for debugging purposes
	logging.debug("input_video: " + input_video)
	logging.debug("contact_sheet: " + contact_sheet)
	logging.debug("frame_interval: " + str(frame_interval))
	logging.debug("frame_quantity: " + str(frame_quantity))
	logging.debug("columns: " + str(columns))
	logging.debug("width: " + str(width))
	logging.debug("margin: " + str(margin))
	logging.debug("padding: " + str(padding))
	
	sheet = ContactSheet(input_video, contact_sheet, columns, width, margin, padding)
	
	# if only frame_interval is provided, extract frames based on the interval
	if frame_interval and not frame_quantity:
		logging.info("Generating contact sheet with frame interval only: " + frame_interval)
		sheet.create_interval(frame_interval)
	# if only frame_quantity is provided, extract frames based on the quantity
	elif frame_quantity and not frame_interval:
		logging.info("Generating contact sheet with frame quantity only: " + frame_quantity)
		sheet.create_quantity(frame_quantity)
	# if both frame_interval and frame_quantity are provided, 
	# the total number of frames will be the lesser of (video_length/frame_interval, frame_quantity)
	elif frame_quantity and frame_interval:
		video_duration = sheet.get_duration(input_video)		
		logging.debug("Video Duration: " + str(video_duration))
		if math.ceil(video_duration / frame_interval)  <= frame_quantity:
			logging.info("Generating contact sheet with frame interval " + frame_interval + " as the number of frames is less than the limit " + frame_quantity)
			sheet.create_interval(frame_interval)
		else:
			logging.info("Generating contact sheet with the maximum frame quantity " + frame_quantity + " as the number of frames based on frame_interval " +  + frame_quantity + " would exceed the limit.")
			sheet.create_quantity(frame_quantity)
	# if neither frame_interval nor frame_quantity is provided, exit in error 	
	else:
		logging.error("Failed to generate contact sheet: neither frame_interval nor frame_quantity is provided.")
		exit(1)
		
	logging.info("Finished.")


if __name__ == "__main__":
	main()
