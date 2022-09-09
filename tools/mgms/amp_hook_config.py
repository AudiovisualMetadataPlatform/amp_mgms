#!/bin/env amp_python.sif  
#
# NOTE: this should go away when the MGMs are updated to use
# the configuration directly and MGMs get separated into
# different directories
#
import argparse
import logging
from pathlib import Path
import os
from amp.config import load_amp_config
from amp.logging import setup_logging

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--debug', default=False, action='store_true', help="Turn on debugging")    
    args = parser.parse_args()

    # set up the standard logging
    setup_logging(None, args.debug)

    # grab the configuration file
    config = load_amp_config()

    # set amp_root
    amp_root = Path(os.environ['AMP_ROOT'])

    # create the INI file
    logging.info("Creating the MGM configuration file")
    with open(amp_root / "galaxy/tools/amp_mgms/amp_mgm.ini", "w") as f:
        for s in config['mgms']:
            f.write(f'[{s}]\n')
            for k,v in config['mgms'][s].items():
                f.write(f'{k} = {v}\n')
                
if __name__ == "__main__":
    main()
