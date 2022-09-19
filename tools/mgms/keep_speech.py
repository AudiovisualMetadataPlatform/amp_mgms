#!/usr/bin/env amp_python.sif
# need the amp_python environment because we call ffmpeg.

import math
import os
import subprocess
import time
from shutil import copyfile
import argparse
from amp.schema.segmentation import Segmentation
import logging
import amp.logging

# Seconds to buffer beginning and end of audio segments by
buffer = 5

def main():
	parser = argparse.ArgumentParser()
	parser.add_argument("--debug", default=False, action="store_true", help="Turn on debugging")
	parser.add_argument("input_file")
	parser.add_argument("input_segmentation_json")
	parser.add_argument("remove_type")
	parser.add_argument("output_file")
	parser.add_argument("kept_segments_file")
	args = parser.parse_args()
	amp.logging.setup_logging("keep_speech", args.debug)
	logging.info(f"Starting with args {args}")
	(input_file, input_segmentation_json, remove_type, output_file, kept_segments_file) = (args.input_file, args.input_segmentation_json, args.remove_type, args.output_file, args.kept_segments_file)


	logging.info("Reading segmentation file")
	# Turn segmentation json file into segmentation object
	seg_data = Segmentation().from_json(read_json_file(args.input_segmentation_json))
	
	logging.info("Removing silence to get a list of kept segments")
	# Remove silence and get a list of kept segments
	kept_segments = remove_silence(args.remove_type, seg_data, args.input_file, args.output_file)

	logging.info("Writing  output json file")
	# Write kept segments to json file
	write_json_file(kept_segments, args.kept_segments_file)	
	logging.info("Finished.")
	exit(0)

# Given segmentation data, an audio file, and output file, remove silence
def remove_silence(remove_type, seg_data, filename, output_file):
	kept_segments = {}
	start_block = -1  # Beginning of a speech segment
	previous_end = 0  # Last end of a speech segment
	segments = 0  # Num of speech segments

	# For each segment, calculate the blocks of speech segments
	for s in seg_data.segments:
		if should_remove_segment(remove_type, s, start_block) == True:
			# If we have catalogued speech, create a segment from that chunk
			if previous_end > 0 and start_block >= 0:
				kept_segment = create_audio_part(filename, start_block, previous_end, len(kept_segments), seg_data.media.duration)
				kept_segments.update(kept_segment)
				# Reset the variables
				start_block = -1
				previous_end = 0
		elif s.label not in ["silence", "noise", remove_type]:
			# If this is a new block, mark the start
			if start_block < 0:
				start_block = s.start
			previous_end = s.end

	# If we reached the end and still have an open block of speech, output it
	if previous_end > 0:
		kept_segment = create_audio_part(filename, start_block, previous_end, len(kept_segments), seg_data.media.duration)
		kept_segments.update(kept_segment)

	logging.debug("Concatenating files")
	# Concetenate each of the individual parts into one audio file of speech
	concat_files(len(kept_segments), output_file)
	
	return kept_segments

def create_empty_file(output_file):
	tmp_filename = "tmp_blank.wav"
	ffmpeg_out = subprocess.Popen(['ffmpeg', '-f', 'lavfi', '-i', "sine=frequency=1000:duration=5", tmp_filename], universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
	stdout,stderr = ffmpeg_out.communicate()
	logging.debug(stdout)
	logging.debug(stderr)
	copyfile(tmp_filename, output_file)

# Get the start offset after removing the buffer
def get_start_with_buffer(start):
	if start <= buffer:
		return 0
	else:
		return math.floor(start - buffer)

def get_end_with_buffer(end, file_duration):
	if end + buffer > file_duration:
		return file_duration
	else:
		return math.floor(end + buffer)

# Given a start and end offset, create a segment of audio 
def create_audio_part(input_file, start, end, segment, file_duration):
	
	# Create a temporary file name
	tmp_filename = "tmp_" + str(segment) + ".wav"

	start_offset = get_start_with_buffer(start)

	# Convert the seconds to a timestamp
	start_str = time.strftime('%H:%M:%S', time.gmtime(start_offset))

	end_offset = get_end_with_buffer(end, file_duration)

	# Calculate duration of segment convert it to a timestamp
	duration = (end_offset - start_offset)
	duration_str = time.strftime('%H:%M:%S', time.gmtime(duration))

	logging.info("Removing segment starting at " + start_str + " for " + duration_str)

	# Execute ffmpeg command to split of the segment
	ffmpeg_out = subprocess.Popen(['ffmpeg', '-i', input_file, '-ss', start_str, '-t', duration_str, '-acodec', 'copy', tmp_filename], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
	
	stdout,stderr = ffmpeg_out.communicate()

	# Print the output
	logging.info("Creating audio segment " + str(segment))
	logging.debug(stdout)
	logging.debug(stderr)

	return {start_offset : end_offset}

# Take each of the individual parts, create one larger file and copy it to the destination file
def concat_files(segments, output_file):
	logging.debug("Number of segments: " + str(segments))
	# Create the ffmpeg command, adding an input file for each segment created
	if segments > 1:
		ffmpegCmd = ['ffmpeg']
		streams = ""
		for s in range(0, segments):
			streams = streams + "[" + str(s) + ":0]"
			this_segment_name = "tmp_" + str(s) + ".wav"
			ffmpegCmd.append("-i")
			ffmpegCmd.append(this_segment_name)
		streams = streams +  "concat=n=" + str(segments) + ":v=0:a=1[out]"
		ffmpegCmd.extend(['-filter_complex', streams, "-map", "[out]", "output.wav"])

		logging.debug(ffmpegCmd)
		# Run ffmpeg 
		ffmpeg_out = subprocess.Popen(ffmpegCmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
		stdout, stderr = ffmpeg_out.communicate()

		# Print the output
		logging.info("Creating complete audio")
		logging.debug(stdout)
		logging.debug(stderr)

		# Copy the temporary result to the final destination
		copyfile("output.wav", output_file)
	elif segments == 1:
		# Only have one segment, copy it to output file
		copyfile("tmp_0.wav", output_file)
	else:
		create_empty_file(output_file)

	# Cleanup temp files
	cleanup_files(segments)

def cleanup_files(segments):
	# Remove concatenated temporary file
	if os.path.exists("output.wav"):
		os.remove("output.wav") 
	
	if os.path.exists("tmp_blank.wav"):
		os.remove("tmp_blank.wav") 
		
	# Remove each individual part if it exists
	for s in range(0, segments):
		this_segment_name = "tmp_" + str(s) + ".wav"
		if os.path.exists(this_segment_name):
			os.remove(this_segment_name)

def should_remove_segment(remove_type, segment, start_block):
	if (segment.label == "silence" or segment.label == "noise" or segment.label == remove_type) and segment.end - segment.start > 60:
		duration = segment.end - segment.start
		# If it is the middle of the file, account for buffers on both the start and end of the file
		if start_block > 0 and duration > (buffer*2):
			return True
		# If it is the beginning of the file, only account for buffer at the end of the file
		if start_block == 0 and duration > buffer:
			return True
	return False


if __name__ == "__main__":
	main()
