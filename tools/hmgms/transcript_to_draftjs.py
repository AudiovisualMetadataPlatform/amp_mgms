#!/usr/bin/env amp_python.sif

import json
import argparse
import logging
import amp.logging
from amp.fileutils import valid_file, create_empty_file, write_json_file

segments = list()

# Converts AMP Transcript json to Draft JS which is used by the transcript editor.
def main():
	parser = argparse.ArgumentParser()
	parser.add_argument("--debug", default=False, action="store_true", help="Turn on debugging")
	parser.add_argument("from_transcript")
	parser.add_argument("diarization_json")
	parser.add_argument("to_draftjs")
	args = parser.parse_args()
	amp.logging.setup_logging("transcript_to_draftjs", args.debug)
	logging.debug(f"Starting with args {args}")

	# using output instead of input filename as the latter is unique while the former could be used by multiple jobs 
	try:
		# exit to requeue here if Transcript->DraftJs conversion already done
		if valid_file(args.to_draftjs):
			logging.debug("IIIF has already been generated (exit 255)")
			exit(255)
		
		logging.info(f"Converting from Transcript {args.from_transcript} to DraftJs {args.to_draftjs}")
		
		if args.diarization_json is not None and args.diarization_json!='None':
			fill_speakers(args.diarization_json)
		speaker_count = 0
		out_json = dict()
		out_json['entityMap'] = {}
		out_json['blocks'] = []

		# Open the transcribe output
		with open(args.from_transcript) as json_file:
			try:
				json_input = json.load(json_file)
			except ValueError as e:
				raise Exception("Exception: Invalid JSON format for input file", e)

			# Check to see if we have the required input
			if 'results' not in json_input.keys():
				raise Exception("Exception: Missing required results input. ")

			ampResults = json_input['results']	

			if 'words' not in ampResults.keys() or 'transcript' not in ampResults.keys():
				raise Exception("Exception: Missing required words or transcript input. ")

			ampResultsWords = ampResults['words']
			ampTranscript = ampResults['transcript']

			blockWords = list() # Words in this data block
			entityRanges = list() # A list of entity ranges
			lastOffset = 0  # The last offset of a word we searched for
			speaker_name = None
			block_start = None
			this_transcript = ''

			# Iterate through all of the words
			for w in range(0, len(ampResultsWords)):
				word = ampResultsWords[w]
				nextWord = None
				punctuation = ""
				wordText = word['text']

				# Check to see if the next "word" is punctuation.  If so, append it to the current word
				if len(ampResultsWords) > w + 1:
					nextWord = ampResultsWords[w + 1]
					if nextWord['type'] == 'punctuation':
						punctuation += nextWord['text']

				# If the current word is actually a word, create the necessary output
				if word['type'] == 'pronunciation':
					# Use the current position as the key
					key = w
					start = word['start']

					# Record the start of the block
					if block_start is None:
						block_start = start

					# Check to see if speaker has changed
					tmp_speaker_name = get_speaker_name(start, word['end'], speaker_count)

					if speaker_name is None:
						speaker_name = tmp_speaker_name
					
					# If we have more than one word...
					if key > 0:
						# If it is a new speaker, record the words associated with the previous speaker and restart.
						if tmp_speaker_name != speaker_name:
							speaker_count+=1
							# Create the data values necessary 
							data = createData(speaker_name, blockWords, block_start)
							# Add this all as a block.  We only have one since only one speaker
							block = createBlock(0, data, entityRanges, this_transcript)
							out_json['blocks'].append(block)
							
							# Once we have logged a block, reset the values
							blockWords = list() # Words in this data block
							entityRanges = list()
							block_start = start
							this_transcript = ''
							speaker_name = tmp_speaker_name
							lastOffset = 0

					# Append punctuation if there is any
					textWithPunct = wordText + punctuation

					# For this block, generate transcript text
					this_transcript = this_transcript + " " + textWithPunct

					# Create the word
					# if score is present for word and score type is confidence, use the score value; otherwise default to 1.0
					score_value = word['score']['value'] if 'score' in word and word['score']['type'] == 'confidence' else 1.0 
					newWord = {
						'start': start,
						'end': word['end'],
						'confidence': score_value,
						'index':key,
						'punct': textWithPunct,
						'text': wordText
					}

					# Create the entity range
					entityRange = {
						'offset': lastOffset,
						'key': key,
						'length': len(textWithPunct),
						'start': start,
						'end': newWord['end'],
						'confidence': newWord['confidence'],
						'text': wordText
					}

					# Find the offset in the paragraph, starting with the last offset
					lastOffset = len(this_transcript)

					# Create the entity map listing
					out_json['entityMap'][key] = {
						'mutability': 'MUTABLE',
						'type': "WORD",
						'data': entityRange
					}

					# Add this to the entity range
					entityRanges.append(entityRange)

					# Add the word
					blockWords.append(newWord)

				# If it's the end, make sure we get the 
				if w == (len(ampResultsWords) -1):
					data = createData(speaker_name, blockWords, block_start)
					# Add this all as a block.  We only have one since only one speaker
					block = createBlock(0, data, entityRanges, this_transcript)
					out_json['blocks'].append(block)

			# Write the json			
			write_json_file(out_json, args.to_draftjs)

		logging.info(f"Successfully converted from Transcript {args.from_transcript} to DraftJs {args.to_draftjs}")
		exit(0)
	except Exception as e:
		# empty out to_draftjs to tell the following HMGM task command to fail
		create_empty_file(args.to_draftjs)
		logging.exception(f"Failed to convert from Transcript {args.from_transcript} to DraftJs {args.to_draftjs}")	
		exit(1)
	
def createBlock(depth, data, entityRanges, transcript):
	return {
				'depth': depth,
				'data' : data,
				'entityRanges': entityRanges,
				'text' : transcript.strip(),
				'type' : 'paragraph',
				'inlineStyleRanges': []
			}

def createData(speaker, words, start):
	data = dict()
	data['speaker'] = speaker # Generic speaker since we don't have speakers at this point
	data['words'] = words
	data['start'] = start
	return data

def fill_speakers(diarization_json):
	try:
		with open(diarization_json) as diarization_json:
			segmentation = json.load(diarization_json)
			# Conversion already done.  Exit
			if 'segments' in segmentation.keys():
				for s in range(0, len(segmentation['segments'])):
					segments.append(segmentation['segments'][s])
	except ValueError as e:
		raise Exception("Exception: failed to read Diarization json", e)

def get_speaker_name(start, end, speaker_count):
	if len(segments)==0:
		return "Speaker_0"

	name = None
	for s in range(0, len(segments)):
		this_segment = segments[s]
		if this_segment["start"] <= start and this_segment["end"] >= end:
			if 'speakerLabel' in this_segment.keys() and this_segment['speakerLabel'] is not None:
				name = this_segment['speakerLabel']
			elif 'label' in this_segment.keys() and this_segment['label'] is not None:
				name = this_segment['label'] + "_" + str(s)

	if name is None:
		name = "Speaker_" + str(speaker_count)
		speaker_count += 1

	return name


if __name__ == "__main__":
	main()