#!/usr/bin/env python3

import argparse
import json
import logging
import os
import os.path
import shutil
import subprocess
import sys
import uuid

import amp.logger
from amp.schema.speech_to_text import SpeechToText, SpeechToTextMedia, SpeechToTextResult, SpeechToTextWord, SpeechToTextScore
import amp.utils


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", default=False, action="store_true", help="Turn on debugging")
    parser.add_argument("speech_audio")
    parser.add_argument("transcript_txt")
    parser.add_argument("gentle_transcript")
    parser.add_argument("amp_transcript_aligned")
    args = parser.parse_args()
    logging.info(f"Starting with args={args}")
    (speech_audio, transcript_txt, gentle_transcript, amp_transcript_aligned) = (args.speech_audio, args.transcript_txt, args.gentle_transcript, args.amp_transcript_aligned)

    exception = False
    try:
        # prefix random id to original filenames to ensure uniqueness for the tmp Gentle singularity input files 
        id = str(uuid.uuid4())
        tmp_speech_audio_name = "gentle-" + id + "-" + os.path.basename(speech_audio)
        tmp_transcript_txt_name = "gentle-" + id + "-" + os.path.basename(transcript_txt)
        tmp_gentle_transcript_name = "gentle-" + id + "-" + os.path.basename(gentle_transcript)

        # define directory accessible to singularity container
        tmpdir = '/tmp'

        # define tmp filepaths
        tmp_speech_audio = f"{tmpdir}/{tmp_speech_audio_name}"
        tmp_transcript_txt = f"{tmpdir}/{tmp_transcript_txt_name}"
        tmp_gentle_transcript = f"{tmpdir}/{tmp_gentle_transcript_name}"

        # Copy the audio file and transcript text file to a location accessible to the singularity container
        shutil.copy(speech_audio, tmp_speech_audio)
        shutil.copy(transcript_txt, tmp_transcript_txt)

        # Run gentle
        logging.info(f"Running Gentle... tmp_speech_audio: {tmp_speech_audio}, tmp_transcript_txt: {tmp_transcript_txt}, tmp_gentle_transcript: {tmp_gentle_transcript}")
        sif = sys.path[0] + "/gentle_forced_alignment.sif"
        r = subprocess.run(["singularity", "run", sif, tmp_speech_audio, tmp_transcript_txt, "-o", tmp_gentle_transcript], stdout=subprocess.PIPE)
        logging.info(f"Finished running Gentle with return Code: {r.returncode}")

        # if Gentle completed in success, continue with transcript conversion
        if r.returncode == 0:
            # Copy the tmp Gentle output file to gentle_transcript
            shutil.copy(tmp_gentle_transcript, gentle_transcript)

            logging.info("Creating AMP transcript aligned...")
            gentle_transcript_to_amp_transcript(gentle_transcript, speech_audio, amp_transcript_aligned)
        else:
            logging.error("Gentle process failed!")
            
        logging.info("Finished")
        exit(r.returncode)
    except Exception as e:
        logging.exception("Exception while running Gentle.")
        exit(1)


# Convert Gentle output transcript JSON file to AMP Transcript JSON file.
def gentle_transcript_to_amp_transcript(gentle_transcript, speech_audio, amp_transcript_aligned):    
    # read gentle_transcript and initialize pointers
    # note that we use Gentle's transcript instead of the original input transcript, as the former is normalized, while the latter could contain extra spaces and such
    # using Gentle's transcript ensures that the words' offset matches the transcript
    gentle_transcript_json = amp.utils.read_json_file(gentle_transcript)
    transcript = gentle_transcript_json["transcript"]
    gwords = gentle_transcript_json["words"]
    words = list()
    preoffset = 0    # end offset of previous word

    # use last word's end timestamp as the duration 
    lenw = len(gwords)
    if lenw > 0:
        lastword = gwords[lenw-1]
        duration = lastword["end"]
    else:
        duration = 0
    
    # initialize amp_transcript
    media = SpeechToTextMedia(duration, speech_audio)        
    results = SpeechToTextResult(words, transcript)
    amp_transcript = SpeechToText(media, amp_results)
    
    # populate amp_transcript words list, based on gentle_transcript words list
    for gword in gwords:
        # get word info from current gentle word, which is always a pronunciation
        type = "pronunciation"  
        text = gword["word"]
        offset = gword["startOffset"]
        start = gword["start"]
        end = gword["end"]
        scoreType = "confidence"            
        
        # set score value to 1 if word is aligned in success, 0 otherwise
        scoreValue = 1.0 if gword["case"] == "success" else 0.0              
        
        # insert punctuation between the current and previous word if any, based on their offsets;
        # this is needed as Gentle doen't include punctuation in the words list, but the transcript does
        insert_punctuations(results, transcript, preoffset, offset)
            
        # append the current word to the AMP words list
        results.addWord(type, text, offset, start, end, scoreType, scoreValue) 
        preoffset = gword["endOffset"]                                     
        
    # append punctuation after the last word if any text left
    offset = len(transcript)
    insert_punctuations(results, transcript, preoffset, offset)
    logging.info(f"Successfully added {len(words)} words into AMP aligned transcript, including {len(gwords)} words from Gentle words, and {len(words)-len(gwords)} punctuations inserted from Gentle transcript.")
    
    # write final amp_transcript_aligned_json to file
    amp.utils.write_json_file(amp_transcript, amp_transcript_aligned)
        
        
# Insert punctuations to the given results object, if there is any in the given transcript between the previous offset and current offset.
def insert_punctuations(results, transcript, preoffset, offset):                
    # scan transcript between end of previous word and start of current word        
    for i in range(preoffset, offset):
        text = transcript[i]
        
        # only insert non-space chars, which should be punctuations
        if text != ' ':            
            type = "punctuation"  
            offset = i
            scoreType = "confidence"         
            
            # all punctuations have score 0, empty start/end timestamp
            scoreValue = 0.0 
            start = end = None             
            
            # append the current punctuations to the AMP words list
            results.addWord(type, text, offset, start, end, scoreType, scoreValue)     
            logging.debug(f"Insert punctuation as AMP words[{len(words)-1}]={text} at offset {offset}")

        
if __name__ == "__main__":
    main()

#     transcript_txt = "amp_un.json"
#     gentle_transcript = "amp_gen.json"
#     amp_transcript_aligned = "amp_al.json"
#      
#     with open(transcript_txt, "r") as transcript_txt_file:
#         transcript_txt_text = json.load(transcript_txt_file)
#     gentle_transcript_to_amp_transcript(gentle_transcript, transcript_txt_text, amp_transcript_aligned)