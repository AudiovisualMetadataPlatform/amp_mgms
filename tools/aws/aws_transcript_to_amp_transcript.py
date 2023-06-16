#!/usr/bin/env amp_python.sif
import argparse
import logging
import amp.logging
from amp.fileutils import read_json_file, write_json_file, valid_file
#from amp.schema.speech_to_text import SpeechToText, SpeechToTextMedia, SpeechToTextResult
from amp.schema.segmentation import Segmentation, SegmentationMedia
from amp.schema.transcript import Transcript

aws_transcribe_schema = {
    'type': 'object',
    'properties': {
        'jobName': {'type': 'string'},
        'accountId': {'type': 'string'},
        'results': {
            'type': 'object',
            'properties': {
                'transcripts': {
                    'type': 'array', 
                    'items': {
                        'type': 'object',
                        'properties': {'transcript': {'type': 'string'}},
                        'required': ['transcript']
                    }
                },
                'speaker_labels': {
                    'type': 'object',
                    'properties': {
                        'channel_label': {'type': 'string'},
                        'speakers': {'type': 'integer'},
                        'segments': {
                            'type': 'array',
                            'items': {
                                'type': 'object',
                                'properties': {
                                    'start_time': {'type': 'string'},
                                    'speaker_label': {'type': 'string'},
                                    'end_time': {'type': 'string'},
                                    'items': {
                                        'type': 'array',
                                        'items': {
                                            'type': 'object',
                                            'properties': {
                                                'start_time': {'type': 'string'},
                                                'speaker_label': {'type': 'string'},
                                                'end_time': {'type': 'string'}
                                            },
                                            'required': ['start_time', 'speaker_label', 'end_time']
                                        }
                                    },                                    
                                },
								'required': ['start_time', 'speaker_label', 'end_time', 'items']
                            }                            
                        },
                        'items': {
                            'type': 'array',
                            'items': {
                                'type': 'object',
                                'properties': {
                                    'start_time': {'type': 'string'},
                                    'speaker_label': {'type': 'string'},
                                    'end_time': {'type': 'string'},
                                    'type': {'type': 'string'},
                                    'alternatives': {
                                        'type': 'array',
                                        'items': {
                                            'type': 'object',
                                            'properties': {
                                                'confidence': {'type': 'number'},
                                                'content': {'type': 'string'}
                                            },
                                            'required': ['confidence', 'content']
                                        }
                                    }
                                },
                                'required': ['start_time', 'speaker_label', 'end_time', 'type', 'alternatives']
                            }
                        }
                    }
                }
            }
        },
        'status': {'type': 'string'}
    },
    'required': ['jobName', 'accountId', 'results', 'status']
}




def main():
	parser = argparse.ArgumentParser()
	parser.add_argument("--debug", default=False, action="store_true", help="Turn on debugging")
	parser.add_argument("input_audio", help="Input audio file")
	parser.add_argument("aws_transcript", help="Input AWS Transcript JSON file")
	parser.add_argument("amp_transcript", help="Output AMP Transcript file")
	parser.add_argument("amp_diarization", help="Output AMP Diarization file")
	args = parser.parse_args()
	amp.logging.setup_logging("aws_transcript_to_amp_transcript", args.debug)
	logging.info(f"Starting with args {args}")

	# read the AWS transcribe json file
	if not valid_file(args.aws_transcript):
		logging.error(f"{args.aws_transcript} is not a valid file")
		exit(1)
	aws = read_json_file(args.aws_transcript, aws_transcribe_schema)		

	# Fail if we don't have results
	if "results" not in aws.keys():
		logging.error("no results in keys")
		exit(1)

	transcript = Transcript("aws_transcript_to_amp_transcript", "0.1",
			  				 media_filename=args.input_audio)
	tresults = transcript.data['results']
	tresults['transcript'] = ' '.join([x['transcript'] for x in aws['results']['transcripts']])
	for word in aws['results']['items']:
		# the text of the word is the alternative with the highest
		# confidence.
		alt = sorted(word['alternatives'], key=lambda x: x['confidence'], reverse=True)[0]
		transcript.add_word(word['type'], alt['content'], 
		      				float(word.get('start_time', 0)), float(word.get('end_time', 0)),
							score_type="confidence", score_value=float(alt['confidence']))
	
	transcript.save(args.amp_transcript)
	logging.info("Transcript conversion complete")


	# Start segmentation schema with diarization data
	# Create a segmentation object to serialize
	segmentation = Segmentation()

	# Create the media object
	segMedia = SegmentationMedia(transcript.data['media']['duration'], args.input_audio)
	segmentation.media = segMedia
	if "speaker_labels" in aws['results'].keys():
		speakerLabels = aws['results']["speaker_labels"]
		segmentation.numSpeakers = speakerLabels["speakers"]

		# For each segment, get the start time, end time and speaker label
		segments = speakerLabels["segments"]
		for segment in segments:
			segmentation.addDiarizationSegment(float(segment["start_time"]), float(segment["end_time"]), segment["speaker_label"])
		
	# Write the output
	write_json_file(segmentation, args.amp_diarization)
	logging.info(f"Successfully converted {args.aws_transcript} to {args.amp_transcript} and {args.amp_diarization}.")


if __name__ == "__main__":
	main()