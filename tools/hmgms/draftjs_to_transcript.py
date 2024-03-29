#!/usr/bin/env amp_python.sif
import difflib
import json
import string
import argparse
import logging
import amp.logging
from amp.fileutils import write_json_file, valid_file, read_json_file
from pathlib import Path

from amp.schema.speech_to_text import SpeechToText, SpeechToTextMedia, SpeechToTextResult, SpeechToTextScore, SpeechToTextWord
# import aws_transcribe_to_schema

# Convert editor output to standardized json
def main():
    #(root_dir, from_draftjs, original_transcript, to_transcript) = sys.argv[1:5]
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", default=False, action="store_true", help="Turn on debugging")
    parser.add_argument("from_draftjs")
    parser.add_argument("original_transcript")
    parser.add_argument("to_transcript")
    args = parser.parse_args()
    amp.logging.setup_logging("draftjs_to_transcript", args.debug)
    logging.debug(f"Starting with args {args}")

    # using output instead of input filename as the latter is unique while the former could be used by multiple jobs     
    try:
        # if from_draftjs is in error raise exception to notify HMGM job runner to fail the job
         # otherwise if from_draftjs doesn't exist yet, exit to requeue (keep waiting)
        if Path(args.from_draftjs + ".err").exists():
            raise Exception(f"File {args.from_draftjs} is in error, the previous command generating it must have failed.")
        if not valid_file(args.from_draftjs):
            # file isn't there yet -- exit with 255 to requeue
            exit(255)

        logging.info(f"Converting DraftJs {args.from_draftjs} to Transcript {args.to_transcript}")

        data = read_json_file(args.from_draftjs)
        # The original code is slightly scary and doesn't make sense...
        #with open(from_draftjs) as json_file:
        #    d = json.load(json_file)
        #    data = eval(json.dumps(d))  
    
        #read original file for extracting only the confidence score of each word
        original_json = read_json_file(args.original_transcript)
        original_items = original_json["results"]["words"]
    	
        #print("the data in editor output is:",data)
        results = SpeechToTextResult()
        word_type = text = ''
        confidence = start_time = end_time = -1
        duration = 0.0
        
        # draftJS input file here always came from converted and corrected AMP Transcript,
        # so it should always contain 'entityMap', otherwise error should occur        
        #Standardising draft js format
        transcript = ''
        entityMap = data["entityMap"]
        for i in range(0, len(entityMap.keys())):
            punctuation = ''
            if str(i) not in entityMap.keys():
                continue
            entity = entityMap[str(i)]
            if "data" in entity:
                if "text" in entity["data"].keys():
                    text = entity["data"]["text"]
                    if text:
                        transcript += entity["data"]["text"]+" "
                        if text[-1] in string.punctuation: #[',','.','!','?']:
                            punctuation = text[-1]
                            text = text[0:-1]
                if "offset" in entity["data"].keys():
                    offset = entity["data"]["offset"]                    
                if "type" in entity:
                    entity_type = entity["type"]
                    if entity_type == "WORD":
                        word_type = "pronunciation"
                        if "start" in entity["data"]:
                            start_time = float(entity["data"]["start"])

                        if "end" in entity["data"]:
                            end_time = float(entity["data"]["end"])

                        if end_time > duration:
                            duration = end_time
                    else:
                        word_type = entity_type

            results.addWord(word_type, text, offset, start_time, end_time, "confidence",confidence)   
            if len(punctuation) > 0:
                results.addWord('punctuation', punctuation, offset, None, None, "confidence",0.0)

        results.transcript = transcript
        words = results.words
        #Now retrieving the confidence values from the original input file and assigning them to 'results'
        list_items = []
        list_result = []
        for i in range(0,len(original_items)):
            list_items.append(original_items[i]["text"])
        
        for j in range(0, len(words)):
            list_result.append(words[j].text)
        
        d = difflib.Differ()
        res = list(d.compare(list_items, list_result))
        i = j = 0
        word_count = len(words)
        original_item_count = len(original_items)
        logging.debug("original item count: " + str(original_item_count))
        logging.debug("word count: " + str(word_count))
        for ele in res:
            if j >= word_count or i >= original_item_count:
                break
            elif ele.startswith("- "):
                i += 1
            elif len(ele) > 2 and ele[0:2] == "+ ":
                words[j].score.value = 1.0
                j += 1
            elif ele[0:1] == " " and words[j].text == original_items[i]["text"]:
                if ("score" in original_items[i]):
                    words[j].score.value = float(original_items[i]["score"]["value"])
                else:
                    words[j].score.value = 1.0 # default score to 1.0 if not existing originally    
                i += 1
                j += 1
            logging.debug("i: " + str(i) + " j:" + str(j))
            
        # Create the media object
        media = SpeechToTextMedia(duration, args.original_transcript)
    
        # Create the final object
        stt = SpeechToText(media, results)
    
        # Write the output
        write_json_file(stt, args.to_transcript)
        logging.info(f"Successfully converted from DraftJs {args.from_draftjs} to Transcript {args.to_transcript}")
        # as the last command in HMGM, implicitly exit 0 here to let the whole job complete in success
        exit(0)
    except Exception as e:
        # as the last command in HMGM, exit in error to let the whole job fail
        logging.exception(f"Failed to convert from DraftJs {args.from_draftjs} to Transcript {args.to_transcript}")
        exit(1)            


if __name__ == "__main__":
	main()