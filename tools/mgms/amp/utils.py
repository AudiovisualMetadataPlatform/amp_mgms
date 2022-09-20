import configparser
import sys
import os
import json
import stat
import logging
from pathlib import Path
from datetime import datetime


ERR_SUFFIX = ".err"

# Note for the methods below:
# Since Galaxy creates all output files with size 0 upon starting a job, we can't use the existence of output file 
# to decide if the output has been created; rather, we can use its file size and/or content as the criteria.


# Return true if the specified file exists and has contents; false otherwise.
def file_exists(file):
    return os.path.exists(file) and os.stat(file).st_size > 0


# Exit with code 255 if the given (output) file already generated previously.
# This method is typically called by a command with following command depending on it, both called repeatedly, such as in HMGM. 
def exit_if_file_generated(file):        
    # if the file has already been generated, for ex, by the HMGM converter, exit calling command with error code 255 
    # to avoid redundant process, and inform HMGM job runner to reschedule the job till all commands complete.     
    if os.path.exists(file) and os.stat(file).st_size > 0:
        logging.debug("File " + file + " has already been generated, exit 255")
        exit(255)
 
 
# Raise exception if the given (input) file does not exist for processing.
# This method is typically called by a command depending on the previous command's success in a multi-command MGM.
def exception_if_file_not_exist(file):       
    # the exception should stop further processing in the calling command, which could either exit with the exception, 
    # or handle the exception and exit with error code 1, to signal HMGM job runner to fail the whole job in ERROR status
    if not os.path.exists(file) or os.stat(file).st_size == 0:
        raise Exception("Exception: File " + file + " doesn't exist or is empty, the previous command generating it must have failed.")
 
 
# Check if the given (input) file is in error or doesn't exist for processing,  raise exception (error code 1) or exit with 255 respectively.
# This method is typically called by a command repeatedly waiting on the previous command's completion in a multi-command HMGM.
def exit_if_file_not_ready(file):
    # if error file for the given file exists, then previous command (conversion or HMGM task) must have failed,
    # in which case raise exception so the HMGM job runner will fail the whole job in ERROR status
    err_file = file + ERR_SUFFIX
    if os.path.exists(err_file):
        raise Exception("Exception: File " + file + " is in error, the previous command generating it must have failed.")

    # otherwise, if the given file hasn't been generated, for ex, by the HMGM editor, exit with error code 2551, 
    # so the HMGM job runner can requeue the job, and process will continue to wait for HMGM task to be completed
    if not os.path.exists(file) or os.stat(file).st_size == 0:
        logging.debug("File " + file + " has not been generated, exit 255")
        exit(255)
         

# Empty out the content of the given (output) file as needed.
# This method is typically called by an MGM command exiting with error code 1 upon exceptions.
def empty_file(file):
    # overwrite the given file to empty if it had contents, so no invalid output is generated in case of exception
    if os.path.exists(file) and os.stat(file).st_size > 0:
        with open(file, 'w') as fp: 
            pass    
        logging.debug("File " + file + " has been emptied out")
    
 
# Create an empty error file for the given (output) file to indicate it's in error.
# This method is typically called by an MGM command exiting with error code 1 upon exceptions.
def create_err_file(file):
    # error file has the .err suffix added to the original file path
    err_file = file + ERR_SUFFIX
    with open(err_file, 'w') as fp: 
        pass
    logging.debug("Error file for " + file + " has been created")
    
 
# Clean up error file if existing for the given (output) file. 
# This method is typically called by an MGM command which could be rerun using the same dependencies after failing with previous error file.
def cleanup_err_file(file):
    err_file = file + ERR_SUFFIX
    if os.path.exists(err_file):
        os.remove(err_file)
        logging.debug("Error file for " + file + " has been cleaned up")
        
     
# Read/parse the given JSON input_file and return the validated JSON dictionary.
def read_json_file(input_file):
    with open(input_file, 'r', encoding='utf8') as file:
        input_json = json.load(file)
    return input_json
        
                
# Serialize the given object and write it to the given JSON output_file
def write_json_file(object, output_file):
    with open(output_file, 'w', encoding='utf8') as file:
        json.dump(object, file, indent = 4, default = lambda x: x.__dict__)
        
# Write the given string to the given text output_file
def write_text_file(string, output_file):
    with open(output_file, 'w', encoding='utf8') as file:
        file.write(string)
        
        
# Get the configuration file
def get_config():
	config = configparser.ConfigParser()
	config.read(sys.path[0] + "/amp_mgm.ini")    
	return config
    

# Get the absolute path of the specified module/mgm working directory
def get_work_dir(work_dir):
    # The original implementation looked it up in the .ini file, but this should be something that "just works".  
    # With that in mind, this will create a working directory next to the script with the work_dir parameter as the subdirectory.
    wd = Path(sys.path[0], work_dir)
    wd.mkdir(parents=True, exist_ok=True)
    logging.debug(f"Getting/Creating workdir: {wd!s}")
    return str(wd.absolute())


# get the Azure credentials from the config file and return them as a dict.
def get_azure_credentials():
    config = get_config()
    res = config._sections['azure']
    logging.debug(f"Azure credentials: {res}")
    return res



