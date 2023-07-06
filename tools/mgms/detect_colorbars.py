#!/usr/bin/env amp_python.sif

# Detect color bars
# Traditionally the bars are accompanied by a 1KHz tone, but for now we're only
# interested in the video.
# 
# We're going to use a FFMPEG filter complex that will subtract the video from
# a generated colorbars video and then track the blackness of the frames.
# 
# One major caveat -- the bottom 1/3 of the frame contains castellations and
# non-color signal information (YIQ data) so we're going to cheat a little bit 
# by only doing the difference on the top 2/3rds of the frame.



import argparse
import logging
import subprocess
import amp.logging
import json

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", default=False, action="store_true", help="Turn on debugging")
    parser.add_argument("input_video", help="Input video file")
    parser.add_argument("amp_segments", help="AMP segment output file")
    parser.add_argument("--frame_difference", type=float, default=0.05, help="Decimal percentage of allowed frame difference")
    parser.add_argument("--pixel_threshold", type=float, default=0.10, help="Decimal percentage of allowed pixel difference")    
    parser.add_argument("--min_gap", type=float, default=0.1, help="Minimum gap between segments")
    parser.add_argument("--min_len", type=float, default=0.9, help="Minimum segment length")
    parser.add_argument("--debug_video", type=str, help="Send the difference video here for debugging")
    args = parser.parse_args()
    amp.logging.setup_logging("detect_colorbars", args.debug)
    logging.info(f"Starting with args {args}")

    # since some of the MDPI videos are in pseudo-IMX50 there is a ton of black
    # space around the frames and we need to crop them.  Scan the video to find
    # the actual picture area
    crop = get_video_crop(args.input_video)
    logging.info(f"Detected video crop: {crop}")
    
    # find the duration
    info = get_video_info(args.input_video)
    duration = 0
    for stream in info['streams']:
        if stream['codec_type'] == "video":
            duration = stream['duration']
            break
    else:
        logging.error("This is not a file with a video in it")
        exit(1)

    debug_video = ['-an', '-f', 'null', '-']
    if args.debug_video:
        debug_video = ['-c:a', 'copy', args.debug_video]


    # some useful tidbits: 
    # https://stackoverflow.com/questions/58971875/is-there-a-way-to-detect-black-on-ffmpeg-video-files
    # https://video.stackexchange.com/questions/29011/ffmpeg-blend-mode-multiply-results-in-green-overlay    
    try:
        with subprocess.Popen(['ffmpeg', '-y',                                                              
                               '-i', args.input_video, 
                               '-f', 'lavfi', '-i', f'smptebars=size={crop[0]}x{crop[1]}:duration={duration}', # generate SMPTE bars                               
                               '-filter_complex', 
                               f"[0:v] crop=w={crop[0]}:h={crop[1]}:x={crop[2]}:y={crop[3]}, format=rgba [video];"  # crop the source video and convert to RGBA
                               "[1:v] format=rgba [colorbars];" # convert the smptebars to RGBA
                               "[colorbars][video] blend=all_mode=subtract:all_opacity=1, format=rgba  [difference];" # get the difference
                               f"[difference] crop=w={crop[0]}:h={int(crop[1] * 0.6)}:x=0:y=0, format=rgba [cropframe];" # only look at the top 2/3rds
                               f"[cropframe] blackdetect=d={args.min_len}:pic_th={1 - args.frame_difference}:pix_th={args.pixel_threshold}", # detect black                               
                               '-shortest', *debug_video],
                               encoding='utf-8',
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT) as p:
            logging.info(f"Black detection command: {p.args}")
            while(line := p.stdout.readline().strip()):
                logging.debug(f"ffmpeg line: {line}")
                if line.startswith("[blackdetect @ "):
                    logging.info(f"Got blackdetect line: {line}")

    except subprocess.SubprocessError as e:
        logging.error(f"Failed to run ffmpeg for main processing: {e}")
        logging.error(f"STDOUT: {e.stdout}")
        exit(1)

    logging.info("FFMPEG has completed")
    logging.info("Finished!")
    
    
def get_video_info(video):
    p = subprocess.run(["ffprobe", "-print_format", "json", 
                        "-show_streams", '-show_format', video],
                        encoding='utf-8', check=True, stdout=subprocess.PIPE, 
                        stdin=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return json.loads(p.stdout)
    

def get_video_crop(video, rate=1/60):
    "Return the video cropping parameters"
    p = subprocess.run(['ffmpeg', '-i', video, 
                        '-vf', f"fps={rate},cropdetect",
                        '-f', 'null', '-'], 
                        stderr=subprocess.STDOUT, stdout=subprocess.PIPE,
                        check=True, encoding='utf-8')
    x = y = 9999
    w = h = 0
    for l in p.stdout.splitlines():
        if not l.startswith('[Parsed_cropdetect'):
            continue
        parts = l.split()
        w = max(w, int(parts[7].split(':')[1]))
        h = max(h, int(parts[8].split(':')[1]))
        x = min(x, int(parts[9].split(':')[1]))
        y = min(y, int(parts[10].split(':')[1]))

    return (w, h, x, y)


if __name__ == "__main__":
    main()