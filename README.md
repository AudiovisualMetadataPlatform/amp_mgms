# amp_mgms
AMP MGMs

These are the standard AMP MGMS

### requirements
* apptainer
* python 3.6+
* make

## Building

Check out this repository into `$AMP_ROOT/src_repos`.  This repo has several submodules, so check this out with:
````
git clone --recursive <this_repo>
````

## Running tests

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

