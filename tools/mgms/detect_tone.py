#!/usr/bin/env amp_python.sif
# Detect 1KHz tone, commonly paired with colorbars
# References:
# * https://klyshko.github.io/teaching/2019-02-22-teaching
#
import argparse
import logging
import subprocess
import amp.logging
from amp.fileutils import write_json_file
import json
from numpy import fft
import numpy as np
import matplotlib.pyplot as plt
import math

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", default=False, action="store_true", help="Turn on debugging")
    parser.add_argument("input_av", help="Input audio/video")
    parser.add_argument("amp_segments", help="AMP segment output file")
    parser.add_argument("--frequency", type=float, default=1000, help="frequency to look for in Hz")
    parser.add_argument("--rate", type=int, default=44100, help="Sample rate per second, must be at least 2x desired frequency")
    parser.add_argument("--tolerance", type=float, default=10, help="frequency tolerance, in Hz")  
    parser.add_argument("--magnitude", type=int, default=2, help="Orders of magnitude needed to isolate frequency")
    parser.add_argument("--showplot", default=False, action="store_true", help="Show a plot at times specified by --plottimes")
    parser.add_argument("--plottimes", type=str, default="0.3,1,10,30,40,50,60", help="Plot times at comma separated time points")
      
    args = parser.parse_args()
    amp.logging.setup_logging("detect_tone", args.debug)
    logging.info(f"Starting with args {args}")

    args.plottimes = [float(x) for x in args.plottimes.split(',')]
    # use ffmpeg to get a raw pcm_u16le @ 44.1KHz audio stream from the source
    try:
        with subprocess.Popen(['ffmpeg', '-y',                                                              
                               '-i', args.input_av, 
                               '-f', 'u16le', '-acodec', 'pcm_u16le',
                               '-ar', str(args.rate), '-ac', '1', '-'],                               
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               stdin=subprocess.DEVNULL) as p:
            logging.info(f"Raw audio command: {p.args}")
            buffer_size = math.ceil(args.rate / 10)
            t = 0
            signal = np.arange(buffer_size)
            segments = []
            start_time = None
            while(d := p.stdout.read(2)):                
                v = d[0] + 256 * d[1]
                signal[t % buffer_size] = v
                t += 1
                if t % buffer_size == 0:
                    # get the current time.
                    tm = t/args.rate                    
                    # run the fft                    
                    fft_spectrum = np.fft.rfft(signal)
                    # get the index->frequency mapping
                    freq = np.fft.rfftfreq(signal.size, d=1/args.rate)
                    # get the log10 absolute value of the spectrum in order to
                    # get the order of magnitude of the amplitude for each frequency
                    fft_spectrum = np.log10(np.abs(fft_spectrum))
                    # clear the 0Hz bucket since it is the sum of all of the
                    # unclassified things (I think) and it will hide the actual data
                    fft_spectrum[0] = 0                    
                    # sort the magnitudes (and frequency index) highest to lowest
                    highest = sorted(enumerate(fft_spectrum), key=lambda x: x[1], reverse=True)                    

                    # grab only the values which are within the desired orders of magnitude 
                    # of the highest frequency found: ie - the "noisiest" frequencies
                    # also, substitute the actual frequency in the first component.
                    highest = [(freq[x[0]], x[1]) for x in highest if abs(x[1] - highest[0][1]) <= args.magnitude]

                    # find any frequencies that are outside of our desired band
                    noise = [x for x in highest if abs(x[0] - args.frequency) > args.tolerance]

                    # If noise was found then our primary signal was not isolated
                    if start_time is not None and noise:
                        # the tone has ended
                        logging.info(f"Tone ends at {tm}")
                        segments.append({'start': start_time, 'end': tm, 'label': 'tone'})
                        start_time = None
                        
                    elif start_time is None and not noise:
                        # the tone has started
                        start_time = tm - buffer_size/args.rate
                        logging.info(f"Tone starts at {start_time}")
                        

                    if args.showplot and tm in args.plottimes:
                        plt.plot(freq, fft_spectrum)
                        plt.title(f"Spectrum at {tm}")
                        plt.xlabel("frequency, Hz")
                        plt.ylabel("Amplitude, units")
                        plt.show()
                    
            if start_time is not None:
                segments.append({'start': start_time, 'end': tm, 'label': 'tone'})



            data = {
                'media': {
                    'filename': args.input_av,
                    'duration': tm,
                },
                'segments': [*segments]
            }

            write_json_file(data, args.amp_segments)
            
    except subprocess.SubprocessError as e:
        logging.error(f"Failed to run ffmpeg for main processing: {e}")
        logging.error(f"STDOUT: {e.stdout}")
        exit(1)
    logging.info("FFMPEG has completed")
    logging.info("Finished!")
    


if __name__ == "__main__":
    main()