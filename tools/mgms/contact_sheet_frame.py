#!/usr/bin/env amp_python.sif

import argparse
import logging
import math

import amp.logging
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
	amp.logging.setup_logging("contact_sheet_frame", args.debug)
	logging.info(f"Starting with args {args}")

	sheet = ContactSheet(args.input_video, args.contact_sheet, args.columns, args.width, args.margin, args.padding)
	
	# if only frame_interval is provided, extract frames based on the interval
	if args.frame_interval and not args.frame_quantity:
		logging.info(f"Generating contact sheet with frame interval only: {args.frame_interval}")
		sheet.create_interval(args.frame_interval)
	# if only frame_quantity is provided, extract frames based on the quantity
	elif args.frame_quantity and not args.frame_interval:
		logging.info(f"Generating contact sheet with frame quantity only: {args.frame_quantity}")
		sheet.create_quantity(args.frame_quantity)
	# if both frame_interval and frame_quantity are provided, 
	# the total number of frames will be the lesser of (video_duration/frame_interval, frame_quantity)
	elif args.frame_quantity and args.frame_interval:
		video_duration = sheet.get_duration(args.input_video)		
		logging.info(f"Video duration: {video_duration} seconds")
		n = math.ceil(video_duration / args.frame_interval)
		if n <= args.frame_quantity:
			logging.info(f"Generating contact sheet with frame interval {args.frame_interval} as the number of frames {n} is less than the limit {args.frame_quantity}")
			sheet.create_interval(args.frame_interval)
		else:
			logging.info(f"Generating contact sheet with the maximum frame quantity {args.frame_quantity} as the number of frames {n} with interval {args.frame_interval} exceeds the limit.")
			sheet.create_quantity(args.frame_quantity)
	# if neither frame_interval nor frame_quantity is provided, exit in error 	
	else:
		logging.error("Failed to generate contact sheet: neither frame_interval nor frame_quantity is provided.")
		exit(1)
		
	logging.info("Finished.")


if __name__ == "__main__":
	main()
