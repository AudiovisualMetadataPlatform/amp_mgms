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

For ex, to run unit tests on the MGMs installed in galaxy (local suite, AWS suite, or some particular test names in local suite):
````
./run_tests.py ../../galaxy/tools/amp_mgms/ local.yaml
./run_tests.py ../../galaxy/tools/amp_mgms/ aws.yaml
./run_tests.py ../../galaxy/tools/amp_mgms/ local.yaml 'Adjust Diarization Timestamps' 'Adjust Transcript Timestamps'
````

## Tests
The test suite has it's own README that gives details about how
it works.

If the MGMs are modified, please make sure that the test suite is
updated accordingly.


## Current status
Everything should be in a working state and ready for shipping.

There are probably some corner cases that need to be worked out.

## Future cleanup / work

* equivalent to "make clean"  Right now, you have to remove the .sif files
  and the kaldi/exp2.tar.gz file manually.
