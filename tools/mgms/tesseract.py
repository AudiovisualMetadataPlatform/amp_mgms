#!/usr/bin/env mgm_python.sif

# Python imports
import argparse
from datetime import datetime
import json
import logging
import os
import pprint
import shlex
import subprocess
import sys
import tempfile
import time

import pytesseract
from pytesseract import Output
from PIL import Image

from amp.schema.video_ocr import VideoOcr, VideoOcrMedia, VideoOcrResolution, VideoOcrFrame, VideoOcrObject, VideoOcrObjectScore, VideoOcrObjectVertices
import amp.logger
import amp.utils


# Python imports
def main():
	with tempfile.TemporaryDirectory(dir = "/tmp") as tmpdir:
		parser = argparse.ArgumentParser()
		parser.add_argument("--debug", default=False, action="store_true", help="Turn on debugging")
		parser.add_argument("input_video", help="Video input file")
		parser.add_argument("dedupe", default=True, help="Whether to dedupe consecutive frames with same texts")
		parser.add_argument("period", default=5, help="Period in seconds to last as consecutive duplicate frames")
		parser.add_argument("amp_vocr", help="Original AMP Video OCR output file")
		parser.add_argument("amp_vocr_dedupe", help="Deduped AMP Video OCR output file")
		args = parser.parse_args()
		logging.info(f"Starting with args={args}")
		(input_video, dedupe, period, amp_vocr, amp_vocr_dedupe) = (args.input_video, args.dedupe, args.period, args.amp_vocr, args.amp_vocr_dedupe)

		dateTimeObj = datetime.now()

		#ffmpeg extracts the frames from the video input
		command = "ffmpeg -i "+input_video+ " -an -vf fps=2 '"+tmpdir+"/frame_%05d_"+str(dateTimeObj)+".jpg'"
		subprocess.call(command, shell=True)
		
		#Tesseract runs the ocr on frames extracted
		script_start = time.time()
		
		# Get some stats on the video
		(dim, duration, frameRate, numFrames) = findVideoMetada(input_video)

		# create AMP VOCR instance
		resolution = VideoOcrResolution(int(dim[0]), int(dim[1]))
		amp_media = VideoOcrMedia(input_video, duration, frameRate, numFrames, resolution)
		frames = []
		
# 		vocr = {"media": {"filename": input_video,
# 					"frameRate": frameRate,
# 					"numFrames": numFrames,
# 					"resolution": {
# 							"width": int(dim[0]),
# 							"height": int(dim[1])
# 						}
# 			
# 				},
# 			"frames": []
# 			}
		
		# for every saved frame
		for num, img in enumerate(sorted(os.listdir(tmpdir))): 
# 			frameList = {"start": str(start_time),
# 				"objects": []
# 				}
		
			# Run OCR
			result = pytesseract.image_to_data(Image.open(tmpdir+"/"+img), output_type=Output.DICT)
			objects = []
			
			# For every result, make an object & add it to the list of boxes for this frame
			for i in range(len(result["text"])): 
				if result["text"][i].strip(): #if the text isn't empty/whitespace
					vertices = VideoOcrObjectVertices(						
						result["left"][i] / resolution.width, 
						result["top"][i] / resolution.height,
						(result["left"][i] + result["width"][i]) / resolution.width, 
						(result["top"][i] + result["height"][i]) / resolution.height)
					score = VideoOcrObjectScore("confidence", result["conf"][i])
					object = VideoOcrObject(result["text"][i], score, vertices)
					objects.append(object)
# 					box = {
# 						"text": result["text"][i],
# 						"score": {
# 							"type":"confidence",
# 							"value": result["conf"][i]
# 								},
# 							# relative coords
# 							"vertices": {
# 							"xmin": result["left"][i]/vocr["media"]["resolution"]["width"],
# 							"ymin": result["top"][i]/vocr["media"]["resolution"]["height"],
# 							"xmax": (result["left"][i] + result["width"][i])/vocr["media"]["resolution"]["width"],
# 							"ymax": (result["top"][i] + result["height"][i])/vocr["media"]["resolution"]["height"]
# 							}
# 						}
# 					frame["objects"].append(box)
		
			# add frame if it had text
			if len(objects) > 0:
				start_time =+ (.5 * num) 
				frame = VideoOcrFrame(start_time, objects)
				frames.append(frame)
# 			if len(frameList["objects"]) > 0:
# 				vocr["frames"].append(frameList)
		
		# create and save the AMP VOCR instance
		vocr = VideoOcr(amp_media, frames)					
		amp.utils.write_json_file(vocr, amp_vocr)
		
		# if dedupe, create and save the deduped AMP VOCR
		if dedupe:
			vocr_deduped = vocr.dedupe(period)
			amp.utils.write_json_file(vocr_deduped, amp_vocr_deduped)
		
		logging.info("Finished.")
		

# UTIL FUNCTIONS
def findVideoMetada(pathToInputVideo):
	cmd = "ffprobe -v quiet -print_format json -show_streams"
	args = shlex.split(cmd)
	args.append(pathToInputVideo)
	
	# run the ffprobe process, decode stdout into utf-8 & convert to JSON
	ffprobeOutput = subprocess.check_output(args).decode('utf-8')
	ffprobeOutput = json.loads(ffprobeOutput)

	# prints all the metadata available:  ---->for debugging
	#pp = pprint.PrettyPrinter(indent=2)
	#pp.pprint(ffprobeOutput)

	#find height and width
	height = ffprobeOutput['streams'][0]['height']
	width = ffprobeOutput['streams'][0]['width']
	duration = ffprobeOutput['streams'][0]['duration']
	frame_rate = ffprobeOutput['streams'][0]['avg_frame_rate']
	numFrames = ffprobeOutput['streams'][0]['nb_frames']

	return ([height, width], duration, frame_rate, numFrames)


if __name__ == "__main__":
	main()
