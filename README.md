# amp_mgms
AMP MGMs

Build all of the MGMs in one go.

## Build requirements
* singularity
* python 3.6+

## Current status
This is the first pass to clean up the MGMs that were used during the 
pilot and get them ready for production use.

The goal for this first phase is to:
* get all of the MGM (and singularity) sources into a single repository
* a unified build process which will build the MGMs with one command
* the scripts should parse their arguments using argparse rather than 
  sys.argv[] -- note that the conversion is hacky and certainly not 
  best practice.
* move source files and modules around so they use python namespaces rather 
  than implied search paths

## Future cleanup

* reduce the size of the .sif files by cleaning up any intermediate build
  files.
* use the args namespace directly, rather than that hacky tuple assignment
* proper logging, rather than ovewriting sys.stderr and sys.stdout 
* some tools require the galaxy root_dir variable.  Is this really needed?