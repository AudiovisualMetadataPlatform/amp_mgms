#!/usr/bin/env python3

import json
import os
import sys
import argparse

from amp.schema.speech_to_text import SpeechToText
from amp.adjustment import Adjustment

from amp.logger import MgmLogger
import amp.utils


def main():

    #(stt_json, adj_json, output_json) = sys.argv[1:4]
    parser = argparse.ArgumentParser()
    parser.add_argument("stt_json")
    parser.add_argument("adj_json")
    parser.add_argument("output_json")
    args = parser.parse_args()
    (stt_json, adj_json, output_json) = (amp.stt_json, amp.adj_json, amp.output_json)


    # Turn adjustment data into list of kept segments
    with open(adj_json, 'r') as file:
        adj_data = json.load(file)

    # Turn stt json into objects
    with open(stt_json, 'r') as file:
        stt = SpeechToText().from_json(json.load(file))
    
    # List of adjustments (start, end, adjustment)
    offset_adj = []
    # Last ending position for iterating through kept segments
    last_end = 0.00
    # Running tally of removed segment lengths
    current_adj = 0.00

    # For each segment that was kept, keep track of the gaps to know how much to adjust
    for kept_segment in adj_data:
        print(kept_segment + ":" + str(adj_data[kept_segment]))
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
    amp.utils.write_json_file(stt, output_json)

def adjust_word(word, offset_adj):
    print(f"WORD: {word.start} : {word.end}")
    # Get the adjustment for which the word falls within it's start and end
    for adj in offset_adj:
        if word.start is not None and word.start >= adj.start and word.start <= adj.end:
            print("STT Offset:" + str(word.start) + " Adjusted Offset:" + str(word.start + adj.adjustment))
            word.start = word.start + adj.adjustment
            word.end = word.end + adj.adjustment
            return
    print("No adjustment found")
    
    
if __name__ == "__main__":
    main()