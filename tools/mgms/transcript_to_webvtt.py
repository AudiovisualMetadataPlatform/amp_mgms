#!/usr/bin/env amp_python.sif
import os
import argparse
import logging
import amp.logging
from amp.vtt_helper import words2phrases, gen_vtt
from amp.fileutils import read_json_file

# Reads the AMP Transcript and Segment inputs and convert them to Web VTT output.
def main(): 
	parser = argparse.ArgumentParser()
	parser.add_argument("--debug", default=False, action="store_true", help="Turn on debugging")
	parser.add_argument("--phrase_gap", default=1.5, type=float, help="Gap between VTT phrases")
	parser.add_argument("--max_duration", default=3.0, type=float, help="Maximum VTT phrase duration")
	parser.add_argument("seg_file")
	parser.add_argument("stt_file")
	parser.add_argument("vtt_file")
	args = parser.parse_args()
	amp.logging.setup_logging("transcript_to_webvtt", args.debug)
	logging.info(f"Starting with args {args}")

	# the diarization should actually be part of the transcript, but since it isn't
	# (and it's in the segmentation), we'll need to do a merging of some sort...
	# Read the diarization json file and convert it to a list of triples: (start, stop, speaker)
	diarization_segments = []
	try:
		diarization_data = read_json_file(args.seg_file)
		diarization_segments = [{'start': x['start'], 
								'end': x['end'], 
								'speaker': x['speakerLabel']} for x in diarization_data['segments']]
	except Exception:
		# it didn't load so we don't care.
		pass

	# Read the transcript and convert it into something that words2phrases wants.
	amp_transcript = read_json_file(args.stt_file)
	words = []
	phrases = []
	for w in amp_transcript['results']['words']:
		if words and  w['text'] in ('\r', '\n'):
			logging.debug(words)
			phrases.extend(words2phrases(words, phrase_gap=args.phrase_gap, max_duration=args.max_duration))
			logging.debug(phrases[-1])
			words = []
			continue
		w['text'] = w['text'].strip()
		if not w['text']:
			continue
		if 'start' not in w:
			w['start'] = words[-1]['end'] if words else 0
		if 'end' not in w:
			w['end'] = w['start']

		if words and (w.get('type', "pronunciation") != "pronunciation" and w['text'] in "\"'?:;.,-!"):
			# The word is explicitly not pronunciation and we have an
			# existing word, so we'll append it to the previous word.
			words[-1]['word'] += w['text']
			continue

		speaker = [x['speaker'] for x in diarization_segments if x['start'] <= w['start'] <= x['end']]
		speaker = speaker[0] if speaker else None
		words.append({
			'start': w['start'],
			'end': w['end'],
			'word': w['text'].strip(),
			'speaker': speaker
		})
		#print(words[-1])
	
	if words:
		phrases.extend(words2phrases(words, phrase_gap=args.phrase_gap, max_duration=args.max_duration))
	with open(args.vtt_file, "w") as f:
		f.write(gen_vtt(phrases))

   
if __name__ == "__main__":
	main()
		
