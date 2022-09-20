#!/usr/bin/env amp_python.sif


import argparse
import logging

import amp.logging
from amp.fileutils import read_json_file, write_json_file, valid_file
from amp.schema.speech_to_text import SpeechToText, SpeechToTextMedia, SpeechToTextResult, SpeechToTextWord, SpeechToTextScore
from amp.schema.segmentation import Segmentation, SegmentationMedia

def main():
	#(input_audio, aws_transcript, amp_transcript, amp_diarization) = sys.argv[1:5]
	parser = argparse.ArgumentParser()
	parser.add_argument("--debug", default=False, action="store_true", help="Turn on debugging")
	parser.add_argument("input_audio", help="Input audio file")
	parser.add_argument("aws_transcript", help="Input AWS Transcript JSON file")
	parser.add_argument("amp_transcript", help="Output AMP Transcript file")
	parser.add_argument("amp_diarization", help="Output AMP Diarization file")
	args = parser.parse_args()
	amp.logging.setup_logging("aws_transcript_to_amp_transcript", args.debug)
	logging.info(f"Starting with args {args}")
	(input_audio, aws_transcript, amp_transcript, amp_diarization) = (args.input_audio, args.aws_transcript, args.amp_transcript, args.amp_diarization)

	# read the AWS transcribe json file
	if not valid_file(aws_transcript):
		logging.error(f"{aws_transcript} is not a valid file")
		exit(1)

	aws = read_json_file(aws_transcript)		

	# Fail if we don't have results
	if "results" not in aws.keys():
		logging.error("no results in keys")
		exit(1)

	amp_results = SpeechToTextResult()
	aws_results = aws["results"]

	if "transcripts" not in aws_results.keys():
		logging.error("no transcripts in aws_results")
		exit(1)

	# Parse transcript
	transcripts = aws_results["transcripts"]
	for t in transcripts:
		# assuming each transcript doesn't include space or newline at the end, to keep the format consistent with word list,
		# we should separate transcripts with newline in between
		if not amp_results.transcript:
			# for the first transcript
			amp_results.transcript = t["transcript"]
		else:
			amp_results.transcript = amp_results.transcript + "\n" + t["transcript"]		

	# Fail if we don't have any items
	if "items" not in aws_results.keys():
		logging.error("no items in aws_results")
		exit(1)

	# Parse items (words)
	items = aws_results["items"]
	duration = 0.00
	
	# For each item, get the necessary parts and store as a word
	for item in items:
		alternatives = item["alternatives"]
		# Choose an alternative
		max_confidence = 0.00
		text = ""

		# Each word is stored as an "alternative".  Get the one with the maximum confidence
		for a in alternatives:
			if float(a["confidence"]) >= max_confidence:
				max_confidence = float(a["confidence"])
				text = a["content"]

		end_time = -1
		start_time = -1

		# Two types (punctionation, pronunciation).  Only keep times for pronunciation
		if item["type"] == "pronunciation":
			end_time = float(item["end_time"])
			start_time = float(item["start_time"])

			# If this is the greatest end time, store it as duration
			if end_time > duration:
				duration = end_time
		
		# Add the word to the results
		amp_results.addWord(item["type"], text, None, start_time, end_time, "confidence", max_confidence)
		
	# compute offset for all words in the list
	amp_results.compute_offset();
	
	# Create the media object
	media = SpeechToTextMedia(duration, input_audio)

	# Create the final object
	outputFile = SpeechToText(media, amp_results)

	# Write the output
	write_json_file(outputFile, amp_transcript)

	# Start segmentation schema with diarization data
	# Create a segmentation object to serialize
	segmentation = Segmentation()

	# Create the media object
	segMedia = SegmentationMedia(duration, input_audio)
	segmentation.media = segMedia
	
	if "speaker_labels" in aws_results.keys():
		speakerLabels = aws_results["speaker_labels"]
		segmentation.numSpeakers = speakerLabels["speakers"]

		# For each segment, get the start time, end time and speaker label
		segments = speakerLabels["segments"]
		for segment in segments:
			segmentation.addDiarizationSegment(float(segment["start_time"]), float(segment["end_time"]), segment["speaker_label"])
		
	# Write the output
	write_json_file(segmentation, amp_diarization)
	logging.info(f"Successfully converted {aws_transcript} to {amp_transcript} and {amp_diarization}.")


if __name__ == "__main__":
	main()