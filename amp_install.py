#!/bin/env python3
#
# Installation and configuration stuff
#

import argparse
import logging
import yaml
from pathlib import Path
from amp_bootstrap_utils import get_amp_root

def install(amp_root, config):    
    logging.info("No module specific installation required")    
    print(amp_root, config)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--debug', default=False, action='store_true', help="Turn on debugging")
    parser.add_argument('config_file', help="Configuration file")
    args = parser.parse_args()
    logging.basicConfig(format="%(asctime)s [%(levelname)-8s] (%(filename)s:%(lineno)d)  %(message)s",
                        level=logging.DEBUG if args.debug else logging.INFO)

    with open(args.config_file) as f:
        config = yaml.safe_load(f)

    # don't know what to do right now..    
    if False:
        install_root = get_amp_root('amp_mgms')    
        galaxy_install_root = get_amp_root('galaxy')

        # symlink a couple of the galaxy tool directories so we can use them.
        for n in ('tools/data_source', 'tools/cloud'):
            try:
                if (install_root / n).exists():
                    (install_root / n).unlink()
                (install_root / n).symlink_to(galaxy_install_root / n)
            except Exception as e:
                logging.error(f"Couldn't symlink {n}: {e}")


if __name__ == "__main__":
    main()
