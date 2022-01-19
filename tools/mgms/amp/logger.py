import sys
import os
from datetime import datetime
import shutil
import zipfile
import gzip

import amp.utils


class MgmLogger(object):
    log_file_size = 1000000
    def __init__(self, root_dir, logname, input_file):
        self.terminal = sys.stdout
        log_file_name = self.create_log_file(root_dir, input_file, logname)
        self.log = open(log_file_name, "a")
        
    def create_log_file(self, root_dir, input_file, logname):
        base_name = os.path.basename(input_file)
        file_name = base_name + "_" + logname + ".log"
        log_path = self.get_log_dir(root_dir)
        log_file_name = os.path.join(log_path, file_name)
        self.roll_log_file(log_file_name)
        return log_file_name.lower()

    def compress_log_file(self, log_file_name):
        base_name = os.path.basename(log_file_name)
        with open(log_file_name, 'rb') as f_in:
            with open(log_file_name + '.gz', 'wb') as f_out:
                with gzip.GzipFile(base_name, 'wb', fileobj=f_out) as f_out:
                    shutil.copyfileobj(f_in, f_out)

    def roll_log_file(self, log_file):
        if os.path.exists(log_file) == False:
            return

        file_stats = os.stat(log_file)
        
        # If the log file is greater than the max size, move it, start with the base log name
        if file_stats.st_size > self.log_file_size:
            # Find the next iterator.  If it's greater than 1000, will keep appending
            for i in range(1,1000):
                tmp_file_name = log_file + "." + str(i)
                if os.path.exists(tmp_file_name)==False:
                    shutil.move(log_file,tmp_file_name)
                    self.compress_log_file(tmp_file_name)
                    os.remove(tmp_file_name)
                    break

    def write(self, message):
        now = datetime.now()
        date_time = now.strftime("%m/%d/%Y %H:%M:%S")
        self.terminal.write(message)
        self.log.write(date_time + "\t" + message + "\n")  
    
    def get_log_dir(self, root_dir):
        return amp.utils.get_log_dir(root_dir)

    def flush(self):
        pass    


# A better implementation of logging which will standardize the format and whatnot.
# * logs go to stderr 
# * if a 'logs' directory exists next to the executable, messages will also be appended to mgms.log
# * the mgms.log will be rotated automatically
# * if --debug appears in the argv, then the level will be set to DEBUG, else INFO
import logging    
import logging.handlers
from pathlib import Path
import fcntl

class TimedRotatingFileHandler(logging.handlers.TimedRotatingFileHandler):
    "Multi-process-safe locking file handler"
    def __init__(self, *args, **kwargs):
        logging.handlers.TimedRotatingFileHandler.__init__(self, *args, **kwargs)
    
    def emit(self, record):        
        x = self.stream # copy the stream in case we rolled
        fcntl.lockf(x, fcntl.LOCK_EX)
        super().emit(record)
        if not x.closed:
            fcntl.lockf(x, fcntl.LOCK_UN)


def setup_logging():
    # IF --debug appears in the arguments, set the level to DEBUG    
    logging_level = logging.DEBUG if '--debug' in sys.argv else logging.INFO    

    formatter = logging.Formatter("%(asctime)s [%(levelname)-8s] (%(filename)s:%(lineno)d:%(process)d)  %(message)s")

    logger = logging.getLogger()
    logger.setLevel(logging_level)

    # set up the console handler
    console = logging.StreamHandler()
    console.setLevel(logging_level)
    console.setFormatter(formatter)
    logger.addHandler(console)

    # set up the file logger (if the logs directory exists next to the script)
    log_path = Path(sys.path[0], "logs")
    if log_path.exists():
        file = TimedRotatingFileHandler(log_path / "mgms.log", when='midnight', encoding='utf-8')
        file.setLevel(logging_level)
        file.setFormatter(formatter)
        logger.addHandler(file)


setup_logging()