#!/bin/env python3
#
# Configuration stuff for amp mgms
#

import argparse
import logging
import yaml
from pathlib import Path
from amp_bootstrap_utils import read_galaxy_config, write_galaxy_config, get_amp_root
import sys
import os

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--debug', default=False, action='store_true', help="Turn on debugging")
    parser.add_argument('--force', default=False, action='store_true', help="Force reconfiguration")
    parser.add_argument('config', help="Configuration file")
    args = parser.parse_args()
    logging.basicConfig(format="%(asctime)s [%(levelname)-8s] (%(filename)s:%(lineno)d)  %(message)s",
                        level=logging.DEBUG if args.debug else logging.INFO)

    with open(args.config) as f:
        config = yaml.safe_load(f)

    # don't know what to do for now.
    if False:
        mgmsdir = Path(sys.path[0]).resolve()
        logging.debug(f"Moving to mgm directory {mgmsdir}")
        os.chdir(mgmsdir)

        galaxydir = get_amp_root('galaxy')
        galaxyconfigfile = galaxydir / "config/galaxy.yml"
        if not galaxyconfigfile.exists():
            logging.error(f"The galaxy configuration file {galaxyconfigfile} doesn't exist.")
            logging.info("Configure galaxy first")
            exit(1)

        logging.info(f"Loading galaxy configuration from {galaxyconfigfile!s}")    
        gconfig = read_galaxy_config(galaxyconfigfile)

        # set tool_config_file and tool_path
        gconfig['galaxy']['tool_config_file'] = str((mgmsdir / 'amp_tool_conf.xml').resolve())
        gconfig['galaxy']['tool_path'] = str((mgmsdir / 'tools').resolve())

        logging.info(f"Saving configuration to {galaxyconfigfile}")
        write_galaxy_config(gconfig, galaxyconfigfile)

if __name__ == "__main__":
    main()
