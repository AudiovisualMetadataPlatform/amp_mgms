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
    # Singularity builds need a lot of disk space. If 
    # SINGULARITY_TMPDIR isn't set, we'll use the temp
    # directory next to this script.  Same for the
    # singularity cache.
    tempdir = Path(sys.path[0], 'temp')
    logging.info(f"Setting tempdir to {tempdir}")
    tempdir.mkdir(exist_ok=True)
    if 'SINGULARITY_TMPDIR' not in os.environ:
        os.environ['SINGULARITY_TMPDIR'] = sys.path[0] + "/temp"
        Path(os.environ['SINGULARITY_TMPDIR']).mkdir(exist_ok=True)
        logging.info(f"Setting SINGULARITY_TMPDIR = {os.environ['SINGULARITY_TMPDIR']}")
    if 'SINGULARITY_CACHEDIR' not in os.environ:
        os.environ['SINGULARITY_CACHEDIR'] = sys.path[0] + "/temp/singularity_cache"
        Path(os.environ['SINGULARITY_CACHEDIR']).mkdir(exist_ok=True, parents=True)
        logging.info(f"Setting SINGULARITY_CACHEDIR = {os.environ['SINGULARITY_CACHEDIR']}")



    logging.info("Building MGMs")
    here = Path.cwd().resolve()
    destdir = Path(args.destdir).resolve()
    for buildscript in here.glob(f"tools/*/mgm_build.sh"):
        # figure out where we're building this
        if args.package:
            buildtmp = tempfile.TemporaryDirectory(prefix='amp_mgms_build-', dir=tempdir)
            builddir = Path(buildtmp.name).resolve()
        else:
            builddir = destdir
    
        logging.info(f"Running build script {buildscript}")
        os.chdir(buildscript.parent)
        cmd = [str(buildscript), str(builddir)]
        if args.debug:
            cmd.append('--debug')
        logging.debug(f"Running command: {cmd}")
        p = subprocess.run(cmd)
        if p.returncode:
            logging.error(f"Build command failed with return code {p.returncode}")            
            exit(1)
        os.chdir(here)

        if args.package:            
            with tempfile.TemporaryDirectory(prefix='amp_mgms_pkg-', dir=tempdir) as tmpdir:
                logging.debug(f"Temporary directory is: {tmpdir}")
                logging.info(f"Copying . to {tmpdir}")
                run_cmd(['cp', '-a', '.', tmpdir], "Copy to tempdir failed", workdir=builddir)

                # TODO: copy amp_install.py and amp_configure.py into the builddir.
                for prog in ('amp_install.py', 'amp_configure.py'):
                    if (here / prog).exists():
                        logging.info(f"Copying {prog} into package")
                        shutil.copy(here / prog, tmpdir)


                if args.version is None:
                    if (buildscript.parent / "mgm_version").exists():
                        with open(buildscript.parent / "mgm_version") as f:
                            args.version = f.readline().strip()

                logging.info(f"Creating package for {buildscript.parent.stem} with version {args.version} in {destdir}")
                outfile = build_package(tmpdir, destdir, f'amp_mgms-{buildscript.parent.stem}', version=args.version, install_path='galaxy')
                logging.info(f"New package {outfile}")


        

if __name__ == "__main__":
    main()
