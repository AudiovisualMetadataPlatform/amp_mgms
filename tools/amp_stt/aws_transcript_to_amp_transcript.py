#!/usr/bin/env python3

import json
import sys

import mgm_utils

from speech_to_text import SpeechToText, SpeechToTextMedia, SpeechToTextResult
from segmentation import Segmentation, SegmentationMedia

def main():
	(media_file, transcribe_file, output_stt_json_file, output_seg_json_file) = sys.argv[1:5]
		
	mgm_utils.exception_if_file_not_exist(transcribe_file)

	# Open the transcribe output
	with open(transcribe_file) as json_file:
		data = json.load(json_file)
		
	amp_results = SpeechToTextResult()

	# Fail if we don't have results
	if "results" not in data.keys():
		exit(1)

	aws_results = data["results"]

	if "transcripts" not in aws_results.keys():
		exit(1)

	# Parse transcript
	transcripts = aws_results["transcripts"]
	for t in transcripts:
		amp_results.transcript = amp_results.transcript + t["transcript"]

	# Fail if we don't have any keys
	if "items" not in aws_results.keys():
		exit(1)

	# Parse items (words)
	items = aws_results["items"]
	duration = 0.00
	
	# For each item, get the necessary parts and store as a word
	for i in items:
		alternatives = i["alternatives"]
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
		if i["type"] == "pronunciation":
			end_time = float(i["end_time"])
			start_time = float(i["start_time"])

			# If this is the greatest end time, store it as duration
			if end_time > duration:
				duration = end_time
		# Add the word to the results
		amp_results.addWord(i["type"], start_time, end_time, text, "confidence", max_confidence)
	
	# Create the media object
	media = SpeechToTextMedia(duration, media_file)

	# Create the final object
	outputFile = SpeechToText(media, amp_results)

	# Write the output
	mgm_utils.write_json_file(outputFile, output_stt_json_file)

	# Start segmentation schema with diarization data
	# Create a segmentation object to serialize
	seg_schema = Segmentation()

	# Create the media object
	segMedia = SegmentationMedia(duration, media_file)
	seg_schema.media = segMedia
	
	if "speaker_labels" in aws_results.keys():
		speakerLabels = aws_results["speaker_labels"]
		seg_schema.numSpeakers = speakerLabels["speakers"]

		# For each segment, get the start time, end time and speaker label
		segments = speakerLabels["segments"]
		for segment in segments:
			seg_schema.addDiarizationSegment(float(segment["start_time"]), float(segment["end_time"]), segment["speaker_label"])
		
	# Write the output
	mgm_utils.write_json_file(seg_schema, output_seg_json_file)


if __name__ == "__main__":
	main()