# amp_mgms
AMP MGMs

Build all of the MGMs in one go.

## Building

This repo has several submodules, so check this out with:
````
git clone --recursive <this_repo>
````

### requirements
* singularity
* python 3.6+
* make

### Process

To build the MGMs and install them in a directory:
````
./amp_build.py <destination directory>
````

To build the MGMs as a distributable package:
````
./amp_build.py --package <package_directory>
````

To run unit tests on the MGMs (command help):  
````
cd tests/
./run_tests.py -h
````

For ex, to run unit tests on the MGMs installed in galaxy (local suite, gentle suite, or some particular test names in local suite):
````
./run_tests.py ../../galaxy/tools/amp_mgms/ local.yaml
./run_tests.py ../../galaxy/tools/amp_mgms/ gentle.yaml
./run_tests.py ../../galaxy/tools/amp_mgms/ local.yaml 'Adjust Diarization Timestamps' 'Adjust Transcript Timestamps'
````


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
* proper logging, rather than ovewriting sys.stderr and sys.stdout.  Logs are
  written to the logs directory that is a peer of the script (if the
  directory exists) and stderr (always)
* some tools require the galaxy root_dir variable.  Is this really needed?
  Turns out, that no, it isn't.
* amp_mgm.ini is a peer of the scripts.  A sample is in the repository
* tool_conf.xml is a galaxy configuration file that can be used to insert
  this toolset into galaxy.

## Future cleanup / work

* reduce the size of the .sif files by cleaning up any intermediate build
  files.
* use the args namespace directly, rather than that hacky tuple assignment
* equivalent to "make clean"  Right now, you have to remove the .sif files
  and the kaldi/exp2.tar.gz file manually.
