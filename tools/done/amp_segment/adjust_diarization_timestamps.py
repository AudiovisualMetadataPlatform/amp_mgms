#!/usr/bin/env python3

import json
import sys

from segmentation import Segmentation
from adjustment import Adjustment

from mgm_logger import MgmLogger
import mgm_utils


def main():

    (segmentation_json, adj_json, output_json) = sys.argv[1:4]

    # Turn adjustment data into list of kept segments
    with open(adj_json, 'r') as file:
        adj_data = json.load(file)

    # Turn segmentation json into objects
    with open(segmentation_json, 'r') as file:
        seg = Segmentation().from_json(json.load(file))
    
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
    print("#OFFSET ADJUSTMENTS")
    for adj in offset_adj:
        print(str(adj.start) + ":" + str(adj.end) + ":"  + str(adj.adjustment))
    # For each word, find the corresponding adjustment
    for segment in seg.segments:
        adjust_segment(segment, offset_adj)
        
    # Write the resulting json
    mgm_utils.write_json_file(seg, output_json)

def adjust_segment(segment, offset_adj):
    print(f"Segment: {segment.start} : {segment.end}")
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
        print("Offset:" + str(segment.start) + " Adjusted Offset:" + str(segment.start + least_adjustment.adjustment))
        segment.start = segment.start + least_adjustment.adjustment
        segment.end = segment.end + least_adjustment.adjustment
    else:
        print("No adjustment found")

    
if __name__ == "__main__":
    main()