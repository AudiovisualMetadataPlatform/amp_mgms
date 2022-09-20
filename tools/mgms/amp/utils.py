import os
import logging

ERR_SUFFIX = ".err"

# Note for the methods below:
# Since Galaxy creates all output files with size 0 upon starting a job, we can't use the existence of output file 
# to decide if the output has been created; rather, we can use its file size and/or content as the criteria.


 
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
        
