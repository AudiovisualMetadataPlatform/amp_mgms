#!/usr/bin/env amp_python.sif

import argparse
from amp.schema.speech_to_text import SpeechToText
from amp.adjustment import Adjustment
import logging
import amp.logging
from amp.fileutils import write_json_file, read_json_file


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", default=False, action="store_true", help="Turn on debugging")
    parser.add_argument("stt_json")
    parser.add_argument("adj_json")
    parser.add_argument("output_json")
    args = parser.parse_args()
    amp.logging.setup_logging("adjust_transcript_timestamps", args.debug)
    logging.info(f"Starting with args {args}")

    # Turn adjustment data into list of kept segments
    adj_data = read_json_file(args.adj_json)

    # Turn stt json into objects
    stt = SpeechToText().from_json(read_json_file(args.stt_json))
    
    # List of adjustments (start, end, adjustment)
    offset_adj = []
    # Last ending position for iterating through kept segments
    last_end = 0.00
    # Running tally of removed segment lengths
    current_adj = 0.00

    # For each segment that was kept, keep track of the gaps to know how much to adjust
    for kept_segment in adj_data:
        logging.debug(kept_segment + ":" + str(adj_data[kept_segment]))
        start = float(kept_segment)
        end = adj_data[kept_segment]
        # If the start of this segment is after the last end, we have a gap
        if(start >= last_end):
            # Keep track of the gap in segments
            current_adj = current_adj + (start - last_end)
            # Add it to a list of adjustments
            offset_adj.append(Adjustment(start - current_adj, end - current_adj, current_adj))
        # Keep track of the last segment end
        last_end = end
    
    # For each word, find the corresponding adjustment
    for word in stt.results.words:
        adjust_word(word, offset_adj)
        
    # Write the resulting json
    write_json_file(stt, args.output_json)
    logging.info("Finished.")

def adjust_word(word, offset_adj):
    logging.debug(f"WORD: {word.start} : {word.end}")
    # Get the adjustment for which the word falls within it's start and end
    for adj in offset_adj:
        if word.start is not None and word.start >= adj.start and word.start <= adj.end:
            logging.debug("STT Offset:" + str(word.start) + " Adjusted Offset:" + str(word.start + adj.adjustment))
            word.start = word.start + adj.adjustment
            word.end = word.end + adj.adjustment
            return
    logging.debug("No adjustment found")
    
    
if __name__ == "__main__":
    main()