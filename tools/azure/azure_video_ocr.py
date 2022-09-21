#!/usr/bin/env amp_python.sif
import logging
import argparse
import logging
import amp.logging
from amp.timeutils import frameToSecond
from amp.fileutils import read_json_file, write_json_file, valid_file
from amp.schema.video_ocr import VideoOcr, VideoOcrMedia, VideoOcrResolution, VideoOcrFrame, VideoOcrObject, VideoOcrObjectScore, VideoOcrObjectVertices
from amp.miscutils import strtobool

def main():
	parser = argparse.ArgumentParser()
	parser.add_argument("--debug", default=False, action="store_true", help="Turn on debugging")
	parser.add_argument("input_video", help="Video input file")
	parser.add_argument("azure_video_index", help="Azure Video Index input file")
	parser.add_argument("azure_artifact_ocr", help="Azure Artifact OCRinput file")
	parser.add_argument("--dedupe", type=strtobool, default='yes', help="Whether to dedupe consecutive frames with same texts")
	parser.add_argument("--dup_gap", type=int, default=5, help="Gap in seconds within which adjacent VOCR frames with same text are considered duplicates")	
	parser.add_argument("amp_vocr", help="Original AMP Video OCR output file")
	parser.add_argument("amp_vocr_dedupe", help="Deduped AMP Video OCR output file")
	args = parser.parse_args()
	amp.logging.setup_logging("azure_video_ocr", args.debug)
	logging.info(f"Starting with args {args}")	
	
	# get Azure video indexer json
	azure_index_json = read_json_file(args.azure_video_index)

	# get Azure artifact OCR json
	# in case Azure Indexer didn't produce OCR artifact, pass in empty json
	azure_ocr_json = read_json_file(args.azure_artifact_ocr) if valid_file(args.azure_artifact_ocr) else None

	# create AMP Video OCR object
	vocr = create_amp_vocr(args.input_video, azure_index_json, azure_ocr_json)
	
	# write AMP Video OCR JSON file
	write_json_file(vocr, args.amp_vocr)
	logging.info(f"Successfully generated AMP VOCR with {len(vocr.frames)} original frames.")
	
	# if dedupe, create the deduped AMP VOCR
	if args.dedupe:
		vocr_dedupe = vocr.dedupe(args.dup_gap)
		write_json_file(vocr_dedupe, args.amp_vocr_dedupe)
		logging.info(f"Successfully deduped AMP VOCR to {len(vocr_dedupe.frames)} frames.")			
	
	
# Create AMP VOCR object from the given Azure indexer json and the OCR artifact json.
def create_amp_vocr(input_video, azure_index_json, azure_ocr_json):
	# create the resolution object
	# Recent versions of azure return the width/height for every frame.  
	# Let"s assume that the data for the first image is indicative of the rest.
	width = azure_ocr_json["Results"][0]["Ocr"]["pages"][0]["width"] if azure_ocr_json else 0
	height = azure_ocr_json["Results"][0]["Ocr"]["pages"][0]["height"] if azure_ocr_json else 0
	resolution = VideoOcrResolution(width, height)

	# create the media object
	frameRate = azure_ocr_json["Fps"] if azure_ocr_json else 0
	duration = azure_index_json["summarizedInsights"]["duration"]["seconds"]
	numFrames = int(frameRate * duration)
	media  = VideoOcrMedia(input_video, duration, frameRate, numFrames, resolution)

	# create AMP VOCR texts from Azure indexer ocr insight
	# we can assume that there is only one video in the Azure indexer json
	# in case Azure Indexer didn't include OCR insight, generate empty texts
	insights = azure_index_json["videos"][0]["insights"]
	ocr_json = insights["ocr"] if insights and "ocr" in insights.keys() else None
	texts = createVocrTexts(ocr_json) if ocr_json else []
	
	# Create AMP VOCR frames from Azure OCR artifact
	# in case Azure Indexer didn't produce OCR artifact, generate empty frames
	frames = createVocrFrames(azure_ocr_json["Results"], frameRate) if azure_ocr_json else []

	vocr = VideoOcr(media, texts, frames)
	return vocr


# Create a list of AMP VOCR texts from the texts list in the given Azure indexer ocr insight json.
def createVocrTexts(ocr_json):
	# BDW: this function doesn't really do anything.
	texts = []
	for ocr in ocr_json:
		for instance in ocr["instances"]:
			text = None
	return texts


# Create a list of AMP VOCR frames from the given Azure OCR artifact results json and the given frame rate.
def createVocrFrames(results_json, fps):
	frames = []
	
	# for each result with text, generate an AMP VOCR frame
	for result in results_json:
		# skip this frame if there is no content (words/lines) in it
		content = result["Ocr"]["content"]
		if not content:
			continue
		
		nframe = result["FrameIndex"]
		start = frameToSecond(nframe, fps)
		objects = []
		
		# for video there should only be one page, but we loop through the page list just in case
		for page in result["Ocr"]["pages"]:
			# we use words instead of lines, because the confidence is only available for each word
			for word in page["words"]:
				text = word["content"]
				confidence = word["confidence"]
				score = VideoOcrObjectScore("confidence", confidence)
				box = word["boundingBox"]	# box[0:7] = (xl, yt, xr, yt, xr, yb, xl, yb)
				vertices = VideoOcrObjectVertices(box[0], box[1], box[4], box[5])
				# language is not provided for words, but available in the ocr insight texts
				# we could get the language by matching content with ocr text, but its computational expensive
				# it's better just to add language in the texts list instead of frames list
				object = VideoOcrObject(text, "", score, vertices)
				objects.append(object)
				
		frame = VideoOcrFrame(start, content, objects)
		frames.append(frame)
	
	return frames


if __name__ == "__main__":
	main()
