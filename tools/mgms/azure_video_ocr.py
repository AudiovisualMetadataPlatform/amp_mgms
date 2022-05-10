#!/usr/bin/env python3
import sys
import logging
import json
import os
from datetime import datetime
import math
import argparse
import logging

import amp.logger
import amp.utils
from amp.schema.video_ocr import VideoOcr, VideoOcrMedia, VideoOcrResolution, VideoOcrFrame, VideoOcrObject, VideoOcrObjectScore, VideoOcrObjectVertices


def main():
	parser = argparse.ArgumentParser()
	parser.add_argument("--debug", default=False, action="store_true", help="Turn on debugging")
	parser.add_argument("input_video", help="Video input file")
	parser.add_argument("azure_video_index", help="Azure video indexer input file")
	parser.add_argument("azure_artifact_ocr", help="Azure Artifact OCR input file")
	parser.add_argument("dedupe", default=True, help="Whether to dedupe consecutive frames with same texts")
	parser.add_argument("dup_gap", default=5, help="Gap in seconds within which adjacent VOCR frames with same text are considered duplicates")	
	parser.add_argument("amp_vocr", help="Original AMP Video OCR output file")
	parser.add_argument("amp_vocr_dedupe", help="Deduped AMP Video OCR output file")
	args = parser.parse_args()
	logging.info(f"Starting with args {args}")
	(input_video, azure_video_index, azure_artifact_ocr, dedupe, dup_gap, amp_vocr, amp_vocr_dedupe) = (args.input_video, args.azure_video_index, args.azure_artifact_ocr, args.dedupe, args.dup_gap, args.amp_vocr, args.amp_vocr_dedupe)
	
	# Get Azure video indexer json
	with open(azure_video_index, "r") as azure_index_file:
		azure_index_json = json.load(azure_index_file)

	# Get Azure artifact OCR json
	with open(azure_artifact_ocr, "r") as azure_ocr_file:
		azure_ocr_json = json.load(azure_ocr_file)

	# Create AMP Video OCR object
	vocr = create_amp_vocr(input_video, azure_index_json, azure_ocr_json)
	
	# write AMP Video OCR JSON file
	amp.utils.write_json_file(vocr, amp_vocr)
	logging.info(f"Successfully generated AMP VOCR with {len(vocr.frames)} original frames.")
	
	# if dedupe, create the deduped AMP VOCR
	if dedupe:
		vocr_dedupe = vocr.dedupe(int(dup_gap))
		amp.utils.write_json_file(vocr_dedupe, amp_vocr_dedupe)
		logging.info(f"Successfully deduped AMP VOCR to {len(vocr_dedupe.frames)} frames.")			
	
	
# Create AMP VOCR object from the given Azure indexer json and the OCR artifact json.
def create_amp_vocr(input_video, azure_index_json, azure_ocr_json):
	# Create the resolution obj
	# Recent versions of azure return the width/height for every frame.  
	# Let"s assume that the data for the first image is indicative of the rest.
	width = azure_ocr_json["Results"][0]["Ocr"]["pages"][0]["width"]
	height = azure_ocr_json["Results"][0]["Ocr"]["pages"][0]["height"]
	resolution = VideoOcrResolution(width, height)

	# Create the media object
	frameRate = azure_ocr_json["Fps"]
	duration = azure_index_json["summarizedInsights"]["duration"]["seconds"]
	numFrames = int(frameRate * duration)
	media  = VideoOcrMedia(input_video, duration, frameRate, numFrames, resolution)

	# Create AMP VOCR texts from Azure indexer ocr insight
	# we can assume that there is only one video in the Azure indexer json
	texts = createVocrTexts(azure_index_json["videos"][0]["insights"]["ocr"])
	
	# Create AMP VOCR frames from Azure OCR artifact
	frames = createVocrFrames(azure_ocr_json["Results"], frameRate)

	vocr = VideoOcr(media, texts, frames)
	return vocr


# Create a list of AMP VOCR texts from the texts list in the given Azure indexer ocr insight json.
def createVocrTexts(ocr_json):
	texts = []
	for ocr in ocr_json:
		for instance in ocr["instances"]:
			text = None
# 					# Get where this term starts and end in terms of frame number
# 					frameIndexStart = getFrameIndex(i["start"], frameRate)
# 					frameIndexEnd = getFrameIndex(i["end"], frameRate)
# 					# Create a temp obj to store the results
# 					newOcr = {
# 						"text" : ocr["text"],
# 						"language" : ocr["language"],
# 						"confidence" : ocr["confidence"],
# 						"left" : ocr["left"],
# 						"top" : ocr["top"],
# 						"width" : ocr["width"],
# 						"height" : ocr["height"]
# 					}
# 					# From the first frame to the last, add the objects info
# 					for frameIndex in range(frameIndexStart, frameIndexEnd + 1):
# 						# If it already exists, append it.  Otherwise create new list
# 						if frameIndex in frame_dict.keys():
# 							thisFrame = frame_dict[frameIndex]
# 							thisFrame.append(newOcr)
# 							frame_dict[frameIndex] = thisFrame
# 						else:
# 							frame_dict[frameIndex] = [newOcr]
	return texts


# Create a list of AMP VOCR frames from the given Azure OCR artifact results json and the given frame rate.
def createVocrFrames(results_json, fps):
	frames = []
	
	# for each result with text, generate an AMP VOCR frame
	for result in results_json:
		# skip this frame if there is no content (words/lines) in it
		content = result["Ocr"]["content"]
		if not content:
			continue
		
		nframe = result["FrameIndex"]
		start = amp.utils.frameToSecond(nframe, fps)
		objects = []
		
		# for video there should only be one page, but we loop through the page list just in case
		for page in result["Ocr"]["pages"]:
			# we use words instead of lines, because the confidence is only available for each word
			for word in page["words"]:
			 	text = word["content"]
			 	confidence = word["confidence"]
			 	score = VideoOcrObjectScore("confidence", confidence)
			 	box = word["boundingBox"]	# box[0:7] = (xl, yt, xr, yt, xr, yb, xl, yb)
			 	vertices = VideoOcrObjectVertices(box[0], box[1], box[4], box[5])
			 	# language is not provided for words, but available in the ocr insight texts
			 	# we could get the language by matching content with ocr text, but its computational expensive
			 	# it's better just to add language in the texts list instead of frames list
			 	object = VideoOcrObject(text, score, vertices)
				objects.append(object)
				
		frame = VideoOcrFrame(start, content, objects)
		frames.append(frame)
	
	return amp_frames


if __name__ == "__main__":
	main()
