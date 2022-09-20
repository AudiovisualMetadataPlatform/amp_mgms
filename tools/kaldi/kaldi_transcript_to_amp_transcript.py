#!/usr/bin/env amp_python.sif

import sys
import os
import argparse
import logging
import amp.utils
from amp.fileutils import read_json_file, write_json_file
from amp.schema.speech_to_text import SpeechToText, SpeechToTextMedia, SpeechToTextResult, SpeechToTextWord, SpeechToTextScore


def main():
	#(input_audio, kaldi_transcript_json, kaldi_transcript_text, amp_transcript) = sys.argv[1:5]
	parser = argparse.ArgumentParser()
	parser.add_argument("--debug", default=False, action="store_true", help="Turn on debugging")
	parser.add_argument("input_audio", help="Input audio file")
	parser.add_argument("kaldi_transcript_json", help="Input Kaldi Transcript JSON file")
	parser.add_argument("kaldi_transcript_text", help="Input Kaldi Transcript Text file")
	parser.add_argument("amp_transcript", help="Output AMP Transcript file")
	args = parser.parse_args()
	convert(args.input_audio, args.kaldi_transcript_json, args.kaldi_transcript_text, args.amp_transcript)
	logging.info(f"Successfully converted {args.kaldi_transcript_json} and {args.kaldi_transcript_text} to {args.amp_transcript}.")

# Convert kaldi output to standardized json
def convert(input_audio, kaldi_transcript_json, kaldi_transcript_text, amp_transcript):
	amp.utils.exception_if_file_not_exist(kaldi_transcript_json)
	# don't fail the job is transcript text is empty, which could be due to no speech in the audio
	if not os.path.exists(kaldi_transcript_text):
		raise Exception("Exception: File " + kaldi_transcript_text + " doesn't exist, the previous command generating it must have failed.")
	results = SpeechToTextResult()

	# Open the kaldi json
	data = read_json_file(kaldi_transcript_json)

	# Get the kaldi transcript
	transcript_file = open(kaldi_transcript_text, "r")	
	results.transcript = transcript_file.read()

	# Get a list of words
	words = data["words"]
	duration = 0.00

	# For each word, add a word to our results
	for w in words:
		start = float(w["time"])
		end = start + float(w["duration"])
		# Keep track of the last time and use it as the duration
		if end > duration:
			duration = end
		results.addWord("pronunciation", w["word"], None, start, end, None, None)

	# compute offset for all words in the list
	results.compute_offset()
	
	# Create the media object
	media = SpeechToTextMedia(duration, input_audio)

	# Create the final object
	stt = SpeechToText(media, results)

	#write the output
	write_json_file(stt, amp_transcript)


if __name__ == "__main__":
	main()
	