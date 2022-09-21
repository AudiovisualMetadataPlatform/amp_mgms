#!/usr/bin/env python3

import os
import os.path
import shutil
import subprocess
import sys
import uuid
import argparse
import logging

def main():
	parser = argparse.ArgumentParser()
	parser.add_argument("--debug", default=False, action="store_true", help="Turn on debugging")
	parser.add_argument("input_file", help="Input file")
	parser.add_argument("json_file", help="Output JSON file")
	args = parser.parse_args()	
	logging.basicConfig(format="%(asctime)s [%(levelname)-8s] (%(filename)s:%(lineno)d:%(process)d)  %(message)s", level=logging.DEBUG if args.debug else logging.INFO)   
	logging.info(f"Started with {args}")
	tmpName = str(uuid.uuid4())
	tmpdir = "/tmp"
	temp_input_file = f"{tmpdir}/{tmpName}.dat"
	temp_output_file = f"{tmpdir}/{tmpName}.json"
	shutil.copy(args.input_file, temp_input_file)
	
	sif = sys.path[0] + "/ina_speech_segmenter.sif"
	#r = subprocess.run(["singularity", "run", sif, temp_input_file, temp_output_file])
	r = subprocess.run([sif, temp_input_file, temp_output_file])

	shutil.copy(temp_output_file, args.json_file)
	if os.path.exists(temp_input_file):
		os.remove(temp_input_file)

	if os.path.exists(temp_output_file):
		os.remove(temp_output_file)
		
	exit(r.returncode)
		
if __name__ == "__main__":
	main()
