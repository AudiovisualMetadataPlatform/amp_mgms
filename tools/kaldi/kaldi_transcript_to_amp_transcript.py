#!/usr/bin/env python3

import sys
import os
import argparse

import amp.utils
from amp.schema.speech_to_text import SpeechToText, SpeechToTextMedia, SpeechToTextResult


# Convert kaldi output to standardized json
def convert(media_file, kaldi_file, kaldi_transcript_file, output_json_file):
	amp.utils.exception_if_file_not_exist(kaldi_file)
	if not os.path.exists(kaldi_transcript_file):
		raise Exception("Exception: File " + kaldi_transcript_file + " doesn't exist, the previous command generating it must have failed.")
	results = SpeechToTextResult()

	# Open the kaldi json
	data = amp.utils.read_json_file(kaldi_file)

	# Get the kaldi transcript
	transcript = open(kaldi_transcript_file, "r")	
	results.transcript = transcript.read()

	# Get a list of words
	words = data["words"]
	duration = 0.00

	# For each word, add a word to our results
	for w in words:
		time = float(w["time"])
		end = time + float(w["duration"])
		# Keep track of the last time and use it as the duration
		if end > duration:
			duration = end
		results.addWord("", time, end, w["word"], None, None)

	# Create the media objeect
	media = SpeechToTextMedia(duration, media_file)

	# Create the final object
	output = SpeechToText(media, results)

	#write the output
	amp.utils.write_json_file(output, output_json_file)

def main():
	#(media_file, kaldi_file, kaldi_transcript_file, output_json_file) = sys.argv[1:5]
	parser = argparse.ArgumentParser()
	parser.add_argument("media_file")
	parser.add_argument("kaldi_file")
	parser.add_argument("kaldi_transcript_file")
	parser.add_argument("output_json_file")
	args = parser.parse_args()
	convert(args.media_file, args.kaldi_file, args.kaldi_transcript_file, args.output_json_file)


if __name__ == "__main__":
	main()