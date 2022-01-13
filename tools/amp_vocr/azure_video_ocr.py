#!/usr/bin/env python3
import sys
import logging
import json
import os
from datetime import datetime
import math
import argparse

from video_ocr import VideoOcr, VideoOcrMedia, VideoOcrResolution, VideoOcrFrame, VideoOcrObject, VideoOcrObjectScore, VideoOcrObjectVertices

import mgm_utils


def main():
	#(input_video, azure_video_index, azure_artifact_ocr, amp_vocr) = sys.argv[1:5]
	parser = argparse.ArgumentParser()
	parser.add_argument("input_video", help="Input video")
	parser.add_argument("azure_video_index", help="Azure video index")
	parser.add_argument("azure_artifact_ocr", help="Azure Artifact OCR")
	parser.add_argument("amp_vocr", help="AMP Video OCR output")
	args = parser.parse_args()
	(input_video, azure_video_index, azure_artifact_ocr, amp_vocr) = (args.input_video, args.azure_video_index, args.azure_artifact_ocr, args.amp_vocr)
	



	# You must initialize logging, otherwise you'll not see debug output.
	logging.basicConfig()

	# Get Azure video index json
	with open(azure_video_index, 'r') as azure_index_file:
		azure_index_json = json.load(azure_index_file)

	# Get Azure artifact OCR json
	with open(azure_artifact_ocr, 'r') as azure_ocr_file:
		azure_ocr_json = json.load(azure_ocr_file)

	# Create AMP Video OCR object
	amp_vocr_obj = create_amp_ocr(input_video, azure_index_json, azure_ocr_json)
	
	# write AMP Video OCR JSON file
	mgm_utils.write_json_file(amp_vocr_obj, amp_vocr)

# Parse the results
def create_amp_ocr(input_video, azure_index_json, azure_ocr_json):
	amp_ocr = VideoOcr()

	# Create the resolution obj
	width = azure_ocr_json["width"]
	height = azure_ocr_json["height"]
	resolution = VideoOcrResolution(width, height)

	# Create the media object
	frameRate = azure_ocr_json["framerate"]	
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
	try:
		x = datetime.strptime(timestamp, '%H:%M:%S.%f')
	except ValueError:
		x = datetime.strptime(timestamp, '%H:%M:%S')
	hourSec = x.hour * 60.0 * 60.0
	minSec = x.minute * 60.0
	total_seconds = hourSec + minSec + x.second + x.microsecond/600000

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
