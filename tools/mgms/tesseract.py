#!/usr/bin/env mgm_python.sif

# Python imports
import argparse
import pytesseract
import os
import json
import sys
import time
import subprocess
import shlex
import pprint
import tempfile
# Python imports
from PIL import Image
from datetime import datetime
from pytesseract import Output
from amp.logger import MgmLogger
import amp.utils

import logging
import amp.logger

def main():
	with tempfile.TemporaryDirectory(dir = "/tmp") as tmpdir:
		#(input_video, amp_vocr) = sys.argv[1:3]
		parser = argparse.ArgumentParser()
		parser.add_argument("--debug", default=False, action="store_true", help="Turn on debugging")
		parser.add_argument("input_video", help="Input video file")
		parser.add_argument("dedupe", default=True, help="Whether to dedupe consecutive frames with same texts")
		parser.add_argument("duration", default=5, help="Duration in seconds to last as consecutive duplicate frames")
		parser.add_argument("amp_vocr", help="Output AMP Video OCR file")
		args = parser.parse_args()
		logging.info(f"Starting with args={args}")
		(input_video, dedupe, duration, amp_vocr, amp_vocr_dedupe) = (args.input_video, args.dedupe, args.duration, args.amp_vocr, args.amp_vocr_dedupe)

		dateTimeObj = datetime.now()

		#ffmpeg extracts the frames from the video input
		command = "ffmpeg -i "+input_video+ " -an -vf fps=2 '"+tmpdir+"/frame_%05d_"+str(dateTimeObj)+".jpg'"
		subprocess.call(command, shell=True)
		
		#Tesseract runs the ocr on frames extracted
		script_start = time.time()
		#amp_vocr =  input_video[:-4]+ "-ocr_"+str(dateTimeObj)+".json"
		
		# Get some stats on the video
		(dim, frameRate, numFrames) = findVideoMetada(input_video)

		vocr = {"media": {"filename": input_video,
					"frameRate": frameRate,
					"numFrames": numFrames,
					"resolution": {
							"width": int(dim[0]),
							"height": int(dim[1])
						}
			
				},
			"frames": []
			}
		
		#for every saved frame
		start_time = 0
		for num, img in enumerate(sorted(os.listdir(tmpdir))): 
			start_time =+ (.5*num) 
			frameList = {"start": str(start_time),
				"objects": []
				}
		
			#Run OCR
			result = pytesseract.image_to_data(Image.open(tmpdir+"/"+img), output_type=Output.DICT)
			
			#For every result, make a box & add it to the list of boxes for this framecalled frameList
			for i in range(len(result["text"])): 
				if result["text"][i].strip(): #if the text isn't empty/whitespace
					box = {
						"text": result["text"][i],
						"score": {
							"type":"confidence",
							"value": result["conf"][i]
								},
							# relative coords
							"vertices": {
							"xmin": result["left"][i]/vocr["media"]["resolution"]["width"],
							"ymin": result["top"][i]/vocr["media"]["resolution"]["height"],
							"xmax": (result["left"][i] + result["width"][i])/vocr["media"]["resolution"]["width"],
							"ymax": (result["top"][i] + result["height"][i])/vocr["media"]["resolution"]["height"]
							}
						}
					frameList["objects"].append(box)
		
				#save frame if it had text
			if len(frameList["objects"]) > 0:
				vocr["frames"].append(frameList)
		
		# save the vocr json file
		amp.utils.write_json_file(vocr, amp_vocr)
		
		# if dedupe, create the deduped AMP VOCR
		if dedupe:
			vocr_deduped = vocr.dedupe(duration)
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
	frame_rate = ffprobeOutput['streams'][0]['avg_frame_rate']
	numFrames = ffprobeOutput['streams'][0]['nb_frames']

	return ([height, width], frame_rate, numFrames)


if __name__ == "__main__":
	main()
