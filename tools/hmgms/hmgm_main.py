#!/usr/bin/env amp_python.sif

import argparse
import json
import logging
import os
import os.path
import shutil
from pathlib import Path
import amp.logging
from amp.config import load_amp_config, get_work_dir
from amp.fileutils import valid_file, create_empty_file, read_json_file
from task.jira import TaskJira
from task.manager import TaskManager
from task.openproject import TaskOpenproject 
from task.redmine import TaskRedmine
from task.trello import TaskTrello
from amp.lwlw import LWLW

MANAGERS = {
	'Jira': TaskJira,
	'OpenProject': TaskOpenproject,
	'Redmine': TaskRedmine,
	'Trello': TaskTrello
}

# It's assumed that all HMGMs generate the output file in the same directory as the input file with ".completed" suffix added to the original filename
HMGM_OUTPUT_SUFFIX = ".complete"
#JIRA = "Jira"
#OPEN_PROJECT = "OpenProject"
#REDMINE = "Redmine"
#TRELLO = "Trello"


# Usage: hmgm_main.py task_type root_dir input_json output_json task_json context_json 
def main():
	# parse command line arguments
	parser = argparse.ArgumentParser()
	parser.add_argument("--debug", default=False, action="store_true", help="Turn on debugging")
	parser.add_argument("--lwlw", default=False, action="store_true", help="Use LWLW protocol")
	parser.add_argument("task_type", help="type of HMGM task: (Transcript, NER, Segmentation, OCR), there is one HMGM wrapper per type")
	parser.add_argument("input_json", help="input file for HMGM task in json format")
	parser.add_argument("output_json", help="output file for HMGM task in json format")
	parser.add_argument("task_json", help="json file storing information about the HMGM task, such as ticket # etc")
	parser.add_argument("context_json", help="context info as json string needed for creating HMGM tasks")
	
	args = parser.parse_args()
	amp.logging.setup_logging("hmgm_main", args.debug)
	logging.debug(f"Starting with args {args}")

	# basic sanity checking
	logging.debug(f"Handling HMGM task: uncorrected JSON: {args.input_json}, corrected JSON: {args.output_json}, task JSON: {args.task_json}")
	# clean up previous error file as needed in case this is a rerun of a failed job
	Path(args.output_json + ".err").unlink(missing_ok=True)
	# as a safeguard, if input_json doesn't exist or is empty, throw exception to fail the job
	# (this means the conversion command failed before hmgm task command)
	if not valid_file(args.input_json):
		logging.error(f"{args.input_json} is not a valid file")
		exit(LWLW.ERROR)
	# if input_json has empty data (not empty file), no need to go through HMGM task, just copy it to the output file, and done
	if empty_input(args.input_json, args.task_type):
		logging.info(f"Input file {args.input_json} for HMGM {args.task_type} editor contains empty data, skipping HMGM task and copy the input to the output")
		shutil.copy(args.input_json, args.output_json)
		exit(LWLW.OK)
	
	# if we get this far, then it's OK to be an LWLW process.
	# using output instead of input filename as the latter is unique while the former could be used by multiple jobs 
	try:
		hmgm = HMGM(args.task_type, args.input_json, args.output_json, args.task_json, args.context_json)
		exit(hmgm.run(lwlw=args.lwlw))
	# upon exception, create error file to notify the following conversion command to fail, and exit 1 (error) to avoid requene
	except Exception as e:
		create_empty_file(args.output_json + ".err")
		logging.exception(f"Failed to handle HMGM task: uncorrected: {args.input_json}, corrected: {args.output_json}, task: {args.task_json}")
		exit(LWLW.ERROR)

	
class HMGM(LWLW):
	def __init__(self, task_type, input_json, output_json, task_json, context_json):
		self.task_type = task_type
		self.input_json = input_json
		self.output_json = output_json
		self.task_json = task_json		
        # Load basic HMGM configuration 
		self.config = load_amp_config()
		# parse the context and desanitize it
		self.context = json.loads(context_json)		
		# all the names were sanitized before passed to context, thus need to be decoded to original values
		for k in ('unitName', 'collectionName', 'itemName', 'primaryfileName', 'workflowName'):
			self.context[k] = self.context[k].replace('%27', "'").replace('%22', '"')
	
		# Create subclass of task manager instance based on task platform specified in the given context.
		manager = self.context["taskManager"]
		assert manager in MANAGERS, f"taskManager {manager} is not one of {[*MANAGERS.keys()]}" 
		self.taskManager = MANAGERS[manager](self.config)


	def exists(self):
		"Return the ID of the job or None if it doesn't exist"
		# Since Galaxy creates all output files with size 0 upon starting a job, we can't use the existence of task_json file 
		# to decide if the task has been created; rather, we can use its file size as the criteria
		# In addition, we could call TaskManager to check the task in the actual task platform, but that's an extra overhead and there is a chance of the task site being down. 
		# Since task_json is only created with task info after a task gets created successfully, we can use it as an indicator of task existence.
		return self.task_json if valid_file(self.task_json) else None


	def submit(self):
		task = create_task(self.taskManager, self.config, self.task_type, self.context, self.input_json, self.output_json, self.task_json)
		logging.info(f"Successfully created HMGM task {task.key}... uncorrected: {self.input_json}, corrected: {self.output_json}, task: {self.task_json}")
		return LWLW.WAIT


	def check(self):		
		editor_output = task_completed(self.config, self.output_json)
		# if HMGM task is completed, close the task and move editor output to output file, and done
		if (editor_output):
			task = close_task(self.taskManager, self.config, self.context, editor_output, self.output_json, self.task_json)
			logging.info(f"Successfully closed HMGM task {task.key}. uncorrected: {self.input_json}, corrected: {self.output_json}, task: {self.task_json}")
			return LWLW.OK
		# otherwise exit 255 to get requeued
		else:
			logging.info(f"Waiting for HMGM task to complete ... uncorrected: {self.input_json}, corrected: {self.output_json}, task: {self.task_json}")
			return LWLW.WAIT    


	def cleanup(self):
		"Clean up everything"
		# remove the temporary input file
		Path(get_editor_input_path(self.config, self.output_json)).unlink(missing_ok=True)
		


# Return true if the given input_json contains empty data based on format defined by the given task_type; false otherwise.
def empty_input(input_json, task_type):
	data = read_json_file(input_json)
	if task_type == TaskManager.TRANSCRIPT:
		return not ('entityMap' in data and len(data['entityMap']) > 0 and 'blocks' in data and len(data['blocks']) > 0)
	elif task_type == TaskManager.NER:
		return not ('annotations' in data and len(data['annotations']) > 0 and 'items' in data['annotations'][0])
	# TODO update below logic	
	elif task_type == TaskManager.SEGMENTATION:
		return True
	elif task_type == TaskManager.OCR:
		return True
 

# If HMGM task has already been completed, i.e. the completed version of the given output JSON file exists, return the output file path; otherwise return False. 
def task_completed(config, output_json):   
	editor_output = get_editor_input_path(config, output_json) + HMGM_OUTPUT_SUFFIX
	if os.path.exists(editor_output):
		return editor_output
	else:
		return False


# Create an HMGM task in the specified task management platform with the given context and input/output files, 
# save information about the created task into a JSON file, and return the created task.
def create_task(taskManager, config, task_type, context, input_json, output_json, task_json):
	# set up the input file in the designated location for HMGM task editor to pick up
	editor_input = setup_editor_input_file(config, input_json, output_json)
	# calling task manager API to create task in the corresponding platform
	return taskManager.create_task(task_type, context, editor_input, task_json)
	
	
# Close the HMGM task specified in the task information file in the corresponding task mamangement platform.
def close_task(taskManager, config, context, editor_output, output_json, task_json):
	# clean up the output file dropped by HMGM task editor in the designated location
	cleanup_editor_output_file(editor_output, output_json)
	# calling task manager API to close task in the corresponding platform
	return taskManager.close_task(task_json)
	
	
# Set up the input file corresponding to the given input JSON file in the designated location for HMGM editors to pick up.     
def setup_editor_input_file(config, input_json, output_json):     
	# TODO update logic here as needed to generate an obscure soft link instead of copying
	# Below we pass the galaxy job output file name to the task editor because the input file name is not unique, 
	# as multiple jobs can run on the same input file, in which case Galaxy pass the same input file path to the tool;
	# meanwhile, the output file name is unique, as Galaxy always creates a new dataset for the output file each time a job is run.
	editor_input = get_editor_input_path(config, output_json)
	shutil.copy(input_json, editor_input)
	return editor_input


# Clean up the output file dropped by HMGM task editors by moving it from the designated location to the output file expected by Galaxy job;
# also, (optionally) remove the corresponding input file in that directory, and return the input file path.
def cleanup_editor_output_file(editor_output, output_json):     
	# move the completed output file to the location expected by Galaxy
	shutil.move(editor_output, output_json)

	editor_input = editor_output[:-len(HMGM_OUTPUT_SUFFIX)]
	# need to check if the original file exists since in case it was never saved to a tmp file it would have been moved to .complete file
	if os.path.exists(editor_input):
		os.remove(editor_input)
	
	return editor_input

	
# Derive the temporary input/output file path used by HMGM tool editors for the given dataset file passed in from the corresponding Galaxy job. 
def get_editor_input_path(config, dataset_file):
	# Note: 
	# For security concerns, we don't pass the original input/output path to HMGM task editors, to avoid exposing the internal Galaxy file system 
	# to external web apps; Instead, we use a designated directory for passing such input/output files, and generate a soft link in 
	# (or copy the file to) this directory, using a filename uniquely mapped from the original filename.  
	io_dir = get_work_dir("hmgm_io") 

	# TODO replace below code with logic to generate an obscure soft link based on the original file path
	# for now we just use the original filename within the designated directory
	filename = os.path.basename(dataset_file)
	filepath = os.path.join(io_dir, filename)
	
	return filepath
	 
	
if __name__ == "__main__":
	main()    
