#!/usr/bin/env amp_python.sif

import argparse
from amp.schema.segmentation import Segmentation
from amp.adjustment import Adjustment
import logging
import amp.logging
from amp.fileutils import write_json_file, read_json_file

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", default=False, action="store_true", help="Turn on debugging")
    parser.add_argument("segmentation_json")
    parser.add_argument("adj_json")
    parser.add_argument("output_json")
    args = parser.parse_args()
    amp.logging.setup_logging("adjust_diarization_timestamps", args.debug)
    logging.info(f"Starting with args {args}")

    # Turn adjustment data into list of kept segments
    adj_data = read_json_file(args.adj_json)

    # Turn segmentation json into objects
    seg = Segmentation().from_json(read_json_file(args.segmentation_json))
    
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
    logging.debug("#OFFSET ADJUSTMENTS")
    for adj in offset_adj:
        logging.debug(str(adj.start) + ":" + str(adj.end) + ":"  + str(adj.adjustment))
    # For each word, find the corresponding adjustment
    for segment in seg.segments:
        adjust_segment(segment, offset_adj)
        
    # Write the resulting json
    write_json_file(seg, args.output_json)
    logging.info("Finished.")

def adjust_segment(segment, offset_adj):
    logging.debug(f"Segment: {segment.start} : {segment.end}")
    # Get the adjustment for which the word falls within it's start and end
    least_diff = None
    least_adjustment = None
    for adj in offset_adj:
        if segment.start is not None and segment.start >= adj.start and segment.start <= adj.end:
            diff = adj.end - segment.start
            if least_diff is None or diff > least_diff:
                least_diff = diff
                least_adjustment = adj
        elif segment.end is not None and segment.end >= adj.start and segment.end <= adj.end:
            diff = segment.end - adj.start
            if least_diff is None or diff > least_diff:
                least_diff = diff
                least_adjustment = adj

    if least_adjustment is not None:
        logging.debug("Offset:" + str(segment.start) + " Adjusted Offset:" + str(segment.start + least_adjustment.adjustment))
        segment.start = segment.start + least_adjustment.adjustment
        segment.end = segment.end + least_adjustment.adjustment
    else:
        logging.debug("No adjustment found")

    
if __name__ == "__main__":
    main()