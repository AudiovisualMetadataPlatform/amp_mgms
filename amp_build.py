#!/bin/env python3
#
# Build the amp-mgms tarball for distribution
#

import argparse
import logging
import tempfile
from pathlib import Path
import shutil
import sys
import yaml
from datetime import datetime
import os
import subprocess
from amp_bootstrap_utils import run_cmd, build_package

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--debug', default=False, action='store_true', help="Turn on debugging")
    parser.add_argument('--version', default=None, help="Package Version")  
    parser.add_argument('--package', default=False, action='store_true', help="build a package instead of installing")
    parser.add_argument('destdir', help="Output directory for package or tool directory root")
    args = parser.parse_args()
    logging.basicConfig(format="%(asctime)s [%(levelname)-8s] (%(filename)s:%(lineno)d)  %(message)s",
                        level=logging.DEBUG if args.debug else logging.INFO)

    # build anything that needs to be built...
    logging.info("Building MGMs")
    here = Path.cwd().resolve()
    if args.package:
        destdir = "/some/directory/i'll/figure/out/later"
    else:
        destdir = Path(args.destdir).resolve()
    
    # Singularity builds need a lot of disk space. If 
    # SINGULARITY_TMPDIR isn't set, we'll use the temp
    # directory next to this script.  Same for the
    # singularity cache.
    if 'SINGULARITY_TMPDIR' not in os.environ:
        os.environ['SINGULARITY_TMPDIR'] = sys.path[0] + "/temp"
        Path(os.environ['SINGULARITY_TMPDIR']).mkdir(exist_ok=True)
        logging.info(f"Setting SINGULARITY_TMPDIR = {os.environ['SINGULARITY_TMPDIR']}")
    if 'SINGULARITY_CACHEDIR' not in os.environ:
        os.environ['SINGULARITY_CACHEDIR'] = sys.path[0] + "/temp/singularity_cache"
        Path(os.environ['SINGULARITY_CACHEDIR']).mkdir(exist_ok=True, parents=True)
        logging.info(f"Setting SINGULARITY_CACHEDIR = {os.environ['SINGULARITY_CACHEDIR']}")

    for script_name in ('mgm_build.sh', 'mgm_build.py'):        
        for buildscript in here.glob(f"tools/*/{script_name}"):
            logging.info(f"Running build script {buildscript}")
            os.chdir(buildscript.parent)
            cmd = [str(buildscript), str(destdir)]
            if args.debug:
                cmd.append('--debug')
            logging.debug(f"Running command: {cmd}")
            p = subprocess.run(cmd)
            if p.returncode:
                logging.error(f"Build command failed with return code {p.returncode}")            
            os.chdir(here)


    if args.package:
        with tempfile.TemporaryDirectory(prefix='amp_mgms_build-') as tmpdir:
            logging.debug(f"Temporary directory is: {tmpdir}")
            logging.info(f"Copying . to {tmpdir}")
            run_cmd(['cp', '-a', '.', tmpdir], "Copy to tempdir failed", workdir=sys.path[0])
            
            # remove git stuff
            run_cmd(['rm', '-rf', '.git'], "Remove git directory", workdir=tmpdir)

            # create the package
            args.destdir = Path(args.destdir).resolve()
            logging.info(f"Creating package in {args.destdir}")
            outfile = build_package(tmpdir, args.destdir, 'amp_mgms', version=args.version)
            print(outfile)


        

if __name__ == "__main__":
    main()
