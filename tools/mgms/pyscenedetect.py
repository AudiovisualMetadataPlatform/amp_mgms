#!/usr/bin/env amp_python.sif

import sys
import traceback
import os
import json
import datetime
import argparse

# Standard PySceneDetect imports:
from scenedetect.video_manager import VideoManager
from scenedetect.scene_manager import SceneManager
# For caching detection metrics and saving/loading to a stats file
from scenedetect.stats_manager import StatsManager

# For content-aware scene detection:
from scenedetect.detectors.content_detector import ContentDetector

from amp.logger import MgmLogger
import amp.utils
import logging
import amp.logger

def main():
    #(input_video, threshold, amp_shots, frame_stats) = sys.argv[1:5]
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", default=False, action="store_true", help="Turn on debugging")
    parser.add_argument("input_video", help="Input video file")
    parser.add_argument("threshold", type=int, default=30, help="Detection sensitivity threshold")
    parser.add_argument("amp_shots", help="AMP Shots Generated")
    parser.add_argument("frame_stats", help="Frame Statistics")
    args = parser.parse_args()
    logging.info(f"Starting with args {args}")
    (input_video, threshold, amp_shots, frame_stats) = (args.input_video, args.threshold, args.amp_shots, args.frame_stats)

    # Get a list of scenes as tuples (start, end) 
#     if threshold is None or isinstance(threshold, int) == False:
#         threshold = 30
#         logging.info("Setting threshold to default because it wasn't a valid integer")
    shots = find_shots(input_video, frame_stats, threshold)

    # Print for debugging purposes
    for shot in shots:
        logging.debug("start: " + str(shot[0]) + "  end: " + str(shot[1]))
    
    # Convert the result to json,
    shots_dict = convert_to_json(shots, input_video)
    
    # save the output json file    
    amp.utils.write_json_file(shots_dict, amp_shots)
    logging.info("Finished.")

# Get the duration based on the last output
def get_duration(shots):
    tc = shots[len(shots) - 1][1].get_timecode()
    return get_seconds_from_timecode(tc)

# Find a list of shots using pyscenedetect api
def find_shots(video_path, stats_file, threshold):
    video_manager = VideoManager([video_path])
    stats_manager = StatsManager()
    # Construct our SceneManager and pass it our StatsManager.
    scene_manager = SceneManager(stats_manager)

    # Add ContentDetector algorithm (each detector's constructor
    # takes detector options, e.g. threshold).
    scene_manager.add_detector(ContentDetector(threshold=threshold))
    base_timecode = video_manager.get_base_timecode()

    scene_list = []

    try:
        # Set downscale factor to improve processing speed.
        video_manager.set_downscale_factor()

        # Start video_manager.
        video_manager.start()

        # Perform scene detection on video_manager.
        scene_manager.detect_scenes(frame_source=video_manager)

        # Obtain list of detected scenes.
        scene_list = scene_manager.get_scene_list(base_timecode)

        # Each scene is a tuple of (start, end) FrameTimecodes.
        logging.debug('List of shots obtained:')
        for i, scene in enumerate(scene_list):
            logging.debug(
                'Scene %2d: Start %s / Frame %d, End %s / Frame %d' % (
                i+1,
                scene[0].get_timecode(), scene[0].get_frames(),
                scene[1].get_timecode(), scene[1].get_frames(),))

        # Save a list of stats to a csv
        if stats_manager.is_save_required():
            with open(stats_file, 'w') as stats_file:
                stats_manager.save_to_csv(stats_file, base_timecode)
    except Exception as err:
        logging.exception(f"Failed to find shots for: video: {video_path}, stats: {stats_file}, threshold: {threshold}")   
    finally:
        video_manager.release()

    return scene_list

def get_seconds_from_timecode(time_string):
    dt = datetime.datetime.strptime(time_string, "%H:%M:%S.%f")
    a_timedelta = dt - datetime.datetime(1900, 1, 1)
    return a_timedelta.total_seconds()

def convert_to_json(shots, input_video):
    duration = get_duration(shots)
    outputDict = {
        "media": {
            "filename": input_video,
            "duration": duration
        },
        "shots": []
    }

    for s in shots:
        start_seconds = get_seconds_from_timecode(s[0].get_timecode())
        end_seconds = get_seconds_from_timecode(s[1].get_timecode())
        shot = {
            "type": "shot",
            "start": start_seconds,
            "end": end_seconds
        }
        outputDict["shots"].append(shot)

    return outputDict


if __name__ == "__main__":
    main()