import numpy as np
from feature import FRAME_SIZE


def smooth(predictions, threshold=0, binary=False):
    if threshold > 0:
        predictions = merge_short_sounds(predictions, threshold)
    grouped = group_frames(predictions, binary)
    return grouped


def merge_short_sounds(predictions, threshold): #TODO: test.. I'm like 95% sure this works
    merged = []
    min_n_frames = round(threshold/FRAME_SIZE)

    previous_value = None
    current_seg_start = 0

    while current_seg_start < len(predictions):
        current_value = predictions[current_seg_start]
        find_next = np.where(predictions[current_seg_start:] != current_value)[0]
        if find_next.size == 0: # if last one
            current_seg_len = len(predictions) - current_seg_start
            next_different = len(predictions)
        else:
            current_seg_len = find_next[0]
            next_different = current_seg_len + current_seg_start

        if current_seg_len >= min_n_frames: # if it's big enough, add & move on
            segment = predictions[current_seg_start:next_different]
            previous_value = current_value
            #print(f"Added {current_seg_len} frames of {current_value}")
        else: # too small
            if not previous_value: # if there hasn't been a long segment yet, just move on
                current_seg_start = next_different
               # print(f"Initial segment, {current_seg_len} frames of {current_value}, skipped")
                continue
            segment = [previous_value]*current_seg_len # make segment the same size w/ previous value
            #print(f"Changed {current_seg_len} frames of {current_value} to {previous_value}")

        merged.extend(segment)
        current_seg_start = next_different

    return merged

def group_frames(predictions, binary):
    i = 0
    current = predictions[0]
    results = []
    while i < len(predictions):
        next_different = np.where(predictions[i:] != current)[0]
        if len(next_different) == 0:  # no more changes in type left.
            results.append({
                "label": num_to_label(current, binary),
                "start": i * FRAME_SIZE/1000,
                "end": (len(predictions)-1) * FRAME_SIZE/1000
            })
            break
        seg_length = int(next_different[0])
        results.append({
            "label": num_to_label(current, binary),
            "start": i* FRAME_SIZE/1000,
            "end": (i+seg_length-1) * FRAME_SIZE/1000
        })
        i += seg_length
        current = predictions[i]
    return results


def num_to_label(i, binary):
    from feature import labels
    keys = list(labels.keys())
    vals = list(labels.values())
    if binary:
        if i > 0:
            return f"non-{keys[0]}"
        return keys[0]
    return keys[vals.index(i)]
