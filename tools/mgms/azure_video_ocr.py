#!/usr/bin/env python3
import sys
import logging
import json
import os
from datetime import datetime
import math
import argparse

from amp.schema.video_ocr import VideoOcr, VideoOcrMedia, VideoOcrResolution, VideoOcrFrame, VideoOcrObject, VideoOcrObjectScore, VideoOcrObjectVertices

import amp.utils
import logging
import amp.logger

def main():
	parser = argparse.ArgumentParser()
	parser.add_argument("--debug", default=False, action="store_true", help="Turn on debugging")
	parser.add_argument("input_video", help="Video input file")
	parser.add_argument("azure_video_index", help="Azure video index input file")
	parser.add_argument("azure_artifact_ocr", help="Azure Artifact OCR input file")
	parser.add_argument("dedupe", default=True, help="Whether to dedupe consecutive frames with same texts")
	parser.add_argument("duration", default=5, help="Duration in seconds to last as consecutive duplicate frames")	
	parser.add_argument("amp_vocr", help="Original AMP Video OCR output file")
	parser.add_argument("amp_vocr_dedupe", help="Deduped AMP Video OCR output file")
	args = parser.parse_args()
	logging.info(f"Starting with args {args}")
	(input_video, azure_video_index, azure_artifact_ocr, dedupe, duration, amp_vocr, amp_vocr_dedupe) = (args.input_video, args.azure_video_index, args.azure_artifact_ocr, args.dedupe, args.duration, args.amp_vocr, args.amp_vocr_dedupe)
	
	# Get Azure video index json
	with open(azure_video_index, 'r') as azure_index_file:
		azure_index_json = json.load(azure_index_file)

	# Get Azure artifact OCR json
	with open(azure_artifact_ocr, 'r') as azure_ocr_file:
		azure_ocr_json = json.load(azure_ocr_file)

	# Create AMP Video OCR object
	amp_vocr_obj = create_amp_ocr(input_video, azure_index_json, azure_ocr_json)
	
	# write AMP Video OCR JSON file
	amp.utils.write_json_file(amp_vocr_obj, amp_vocr)
	
	# if dedupe, create the deduped AMP VOCR
	if dedupe:
		vocr_deduped = vocr.dedupe(duration)
		amp.utils.write_json_file(vocr_deduped, amp_vocr_deduped)
			
	logging.info("Finished.")
	
	
# Parse the results
def create_amp_ocr(input_video, azure_index_json, azure_ocr_json):
	amp_ocr = VideoOcr()

	# Create the resolution obj
	#width = azure_ocr_json["width"]
	#height = azure_ocr_json["height"]
	# Recent versions of azure return the width/height for every frame.  Let's assume
	# that the data for the first image is indicative of the rest.
	width = azure_ocr_json["Results"][0]["Ocr"]["pages"][0]["width"]
	height = azure_ocr_json["Results"][0]["Ocr"]["pages"][0]["height"]
	resolution = VideoOcrResolution(width, height)

	# Create the media object
	#frameRate = azure_ocr_json["framerate"]	
	frameRate = azure_ocr_json["Fps"]
	duration = azure_index_json["summarizedInsights"]["duration"]["seconds"]
	frames = int(frameRate * duration)
	amp_media  = VideoOcrMedia(duration, input_video, frameRate, frames, resolution)
	amp_ocr.media = amp_media

	# Create a dictionary of all the frames [FrameNum : List of Terms]
	frame_dict = createFrameDictionary(azure_index_json['videos'], frameRate)
	
	# Convert to amp frame objects with objects
	amp_frames = createAmpFrames(frame_dict, frameRate)
	
	# Add the frames to the schema
	amp_ocr.frames = amp_frames

	return amp_ocr

# Convert the timestamp to total seconds
def convertTimestampToSeconds(timestamp):
	(h, m, s) = [float(x) for x in timestamp.split(':')]
	total_seconds = (h * 3600) + (m * 60) + s
	return total_seconds

# Calculate the frame index based on the start time and frames per second
def getFrameIndex(start_time, fps):
	startSeconds = convertTimestampToSeconds(start_time)
	frameSeconds = 1/fps
	frameFraction = startSeconds/frameSeconds
	frame = 0.0
	ceilFrame = abs(math.ceil(frameFraction) - frameFraction)
	floorFrame = abs(math.floor(frameFraction) - frameFraction)
	if ceilFrame < floorFrame:
		frame = math.ceil(frameFraction)
	else:
		frame = math.floor(frameFraction)

	return frame

# Create a list of terms for each of the frames
def createFrameDictionary(video_json, frameRate):
	frame_dict={}
	for v in video_json:
		if 'insights' in v and 'ocr' in v['insights']:
			for ocr in v['insights']['ocr']:
				for i in ocr['instances']:
					# Get where this term starts and end in terms of frame number
					frameIndexStart = getFrameIndex(i['start'], frameRate)
					frameIndexEnd = getFrameIndex(i['end'], frameRate)
					# Create a temp obj to store the results
					newOcr = {
						"text" : ocr["text"],
						"language" : ocr["language"],
						"confidence" : ocr["confidence"],
						"left" : ocr["left"],
						"top" : ocr["top"],
						"width" : ocr["width"],
						"height" : ocr["height"]
					}
					# From the first frame to the last, add the objects info
					for frameIndex in range(frameIndexStart, frameIndexEnd + 1):
						# If it already exists, append it.  Otherwise create new list
						if frameIndex in frame_dict.keys():
							thisFrame = frame_dict[frameIndex]
							thisFrame.append(newOcr)
							frame_dict[frameIndex] = thisFrame
						else:
							frame_dict[frameIndex] = [newOcr]
	return frame_dict

# Convert the dictionary into AMP objects we need
def createAmpFrames(frame_dict, frameRate):
	amp_frames = []
	for frameNum, objectList in frame_dict.items():
		objects = []
		for b in objectList:
			amp_score = VideoOcrObjectScore("confidence", b["confidence"])
			bottom = b['top'] - b['height']
			right = b['left'] + b['width']
			amp_vertice = VideoOcrObjectVertices(b['left'], bottom, right, b['top'])
			amp_object = VideoOcrObject(b["text"], b["language"], amp_score, amp_vertice)
			objects.append(amp_object)
		amp_frame = VideoOcrFrame((frameNum) * (1/frameRate), objects)
		amp_frames.append(amp_frame)
	
	amp_frames.sort(key=lambda x: x.start, reverse = False)
	return amp_frames


if __name__ == "__main__":
	main()
