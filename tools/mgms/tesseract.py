#!/usr/bin/env amp_python.sif

# Python imports
import argparse
from datetime import datetime
import json
import logging
import os
import shlex
import subprocess
import tempfile
import time
from distutils.util import strtobool
import pytesseract
from pytesseract import Output
from PIL import Image

from amp.schema.video_ocr import VideoOcr, VideoOcrMedia, VideoOcrResolution, VideoOcrFrame, VideoOcrObject, VideoOcrObjectScore, VideoOcrObjectVertices
import amp.logging

from amp.fileutils import write_json_file

# Python imports
def main():
	with tempfile.TemporaryDirectory(dir = "/tmp") as tmpdir:
		parser = argparse.ArgumentParser()
		parser.add_argument("--debug", default=False, action="store_true", help="Turn on debugging")
		parser.add_argument("input_video", help="Video input file")
		parser.add_argument("vocr_interval", type=float, default=1.0, help="Interval in seconds by which video frames are extracted for VOCR")
		parser.add_argument("dedupe", type=strtobool, default=True, help="Whether to dedupe consecutive frames with same texts")
		parser.add_argument("dup_gap", type=int, default=5, help="Gap in seconds within which adjacent VOCR frames with same text are considered duplicates")
		parser.add_argument("amp_vocr", help="Original AMP Video OCR output file")
		parser.add_argument("amp_vocr_dedupe", help="Deduped AMP Video OCR output file")
		args = parser.parse_args()
		amp.logging.setup_logging("tesseract", args.debug)
		logging.info(f"Starting with args={args}")
		(input_video, vocr_interval, dedupe, dup_gap, amp_vocr, amp_vocr_dedupe) = (args.input_video, args.vocr_interval, args.dedupe, args.dup_gap, args.amp_vocr, args.amp_vocr_dedupe)
	
		# ffmpeg extracts the frames from the video input
		dateTimeObj = datetime.now()
		fps = 1 / vocr_interval;
		command = f"ffmpeg -i {input_video} -an -vf fps={fps} '{tmpdir}/frame_%05d_{dateTimeObj}.jpg'"
		logging.info(f"Extracting frames for VOCR with command {command}")
		subprocess.call(command, shell=True)
		
		# Tesseract runs the ocr on frames extracted
		script_start = time.time()
		
		# Get some stats on the video
		(dim, duration, frameRate, numFrames) = findVideoMetada(input_video)

		# create AMP VOCR instance
		resolution = VideoOcrResolution(int(dim[0]), int(dim[1]))
		amp_media = VideoOcrMedia(input_video, duration, frameRate, numFrames, resolution)
		frames = []		
		
		# for every saved frame run VOCR
		for num, img in enumerate(sorted(os.listdir(tmpdir))): 		
			# Run OCR with Tesseract
			result = pytesseract.image_to_data(Image.open(tmpdir+"/"+img), output_type=Output.DICT)
			objects = []
			
			# For every result, make an object & add it to the list of boxes for this frame
			content = ""
			for i in range(len(result["text"])): 
				text = result["text"][i].strip()
				if text: # if the text isn't empty/whitespace
					content = content + text + " "
					vertices = VideoOcrObjectVertices(						
						result["left"][i] / resolution.width, 
						result["top"][i] / resolution.height,
						(result["left"][i] + result["width"][i]) / resolution.width, 
						(result["top"][i] + result["height"][i]) / resolution.height)
					score = VideoOcrObjectScore("confidence", result["conf"][i])
					object = VideoOcrObject(text, "", score, vertices)
					objects.append(object)
		
			# add frame if it had text
			if len(objects) > 0:
				start_time =+ (vocr_interval * num) 
				frame = VideoOcrFrame(start_time, content, objects)
				frames.append(frame)
		
		# create and save the AMP VOCR instance
		vocr = VideoOcr(amp_media, [], frames)					
		write_json_file(vocr, amp_vocr)
		logging.info(f"Successfully generated AMP VOCR with {len(frames)} original frames.")
		
		# if dedupe, create and save the deduped AMP VOCR
		if dedupe:
			# the duplicate gap should be at least vocr_interval
			gap = max(dup_gap, vocr_interval)
			vocr_dedupe = vocr.dedupe(gap)
			write_json_file(vocr_dedupe, amp_vocr_dedupe)		
			logging.info(f"Successfully deduped AMP VOCR to {len(vocr_dedupe.frames)} frames.")
		

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
