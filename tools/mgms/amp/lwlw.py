# Functionality for LWLW Stuff

import logging
from time import sleep


RC_OK = 0
RC_ERROR = 1
RC_WAIT = 255

class LWLW:
    def __init__(self):
        raise NotImplementedError()

    def check(self) -> int:
        "Check the status of the job"
        raise NotImplementedError()

    def submit(self) -> int:
        "Start a job if it doesn't exist"
        raise NotImplementedError()

    def finalize(self) -> int:
        "Finalize the job by retrieving data and whatnot"
        raise NotImplementedError()

    def cleanup(self) -> None:
        "Cleanup the job"
        raise NotImplementedError()

    def run(self, lwlw=False, refresh=10):
        try:
            if lwlw:
                rc = self.check()
                if rc == None:
                    # job doesn't exist yet, so submit it
                    rc = self.submit()
                if rc == RC_OK:
                    rc = self.finalize()
                if rc != RC_WAIT:
                    self.cleanup()
                exit(rc)
            else:       
                rc = self.check()
                if rc != None:     
                    # cleanup previous job
                    self.cleanup()
                rc = self.submit()
                while rc == RC_WAIT:
                    sleep(refresh)
                    rc = self.check()
                if rc == RC_OK:
                    rc = self.finalize()
                self.cleanup()
                exit(rc)
        except Exception as e:
            logging.exception("LWLW run failed")
            try:
                self.cleanup()
            except Exception:
                logging.exception("Failure cleanup failed")
                