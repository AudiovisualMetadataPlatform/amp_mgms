#!/usr/bin/env python3
import sys
import logging
import json
import os
import argparse
import logging

import amp.logger
import amp.utils
from amp.schema.shot_detection import ShotDetection, ShotDetectionMedia, ShotDetectionShot


def main():
	#(input_video, azure_video_index, amp_shots) = sys.argv[1:4]
	parser = argparse.ArgumentParser()
	parser.add_argument("--debug", default=False, action="store_true", help="Turn on debugging")
	parser.add_argument("input_video")
	parser.add_argument("azure_video_index")
	parser.add_argument("amp_shots")
	args = parser.parse_args()
	logging.info(f"Starting with args {args}")
	(input_video, azure_video_index, amp_shots) = (args.input_video, args.azure_video_index, args.amp_shots)


	# Get Azure video indexer json
	with open(azure_video_index, 'r') as azure_index_file:
		azure_index_json = json.load(azure_index_file)

	# Create AMP Shot object
	amp_shots_obj = create_amp_shots(input_video, azure_index_json)
	
	# write AMP Video OCR JSON file
	amp.utils.write_json_file(amp_shots_obj, amp_shots)
	logging.info("Finished.")


# Parse the results
def create_amp_shots(input_video, azure_index_json):
	amp_shots = ShotDetection()

	# Create the media object
	duration = azure_index_json["summarizedInsights"]["duration"]["seconds"]
	amp_media  = ShotDetectionMedia(input_video, duration)
	amp_shots.media = amp_media

	amp_shots.shots = []
	
	# in our case, there should be only one video in videos, but let's loop through the list just in case
	for video in azure_index_json['videos']:
		if 'insights' in video and 'shots' in video['insights']:
			# Add shots from Azure shots 
			addShots(amp_shots.shots, video['insights']['shots'], 'shot')	
			# Currently we don't use Azure scenes, only shots
# 	 	 	# Add shots from Azure scenes 
# 	 	 	addShots(amp_shots.shots, video['insights']['scenes'], 'scene')
			
	return amp_shots


# Add the given Azure shot list to the given AMP shot list using the given type.
def addShots(amp_shot_list, azure_shot_list, type):
	for shot in azure_shot_list:
		for instance in shot['instances']:
			start = amp.utils.timestampToSecond(instance['start'])
			end = convertTimestampToSeconds(instance['end'])
			shot = ShotDetectionShot(type, start, end)
			amp_shot_list.append(shot)
	# Note: 
	# We can either use each instance of an Azure shot as an AMP shot; or
	# we can combine all instances of an Azure shot (i.e. take start of the first instance and end of the last instance) into one AMP shot.  
	# Here we use the former option. In reality the instances most likely only contain one instance.


if __name__ == "__main__":
	main()
