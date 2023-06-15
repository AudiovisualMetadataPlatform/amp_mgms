# Outside the container

## kaldi.py
This is the external script that starts the container.  

It creates an environment with:
* An overlay of 10x the input file size (minimally 64M)
* A temporary directory is bound to the container's /audio_in
* the input file is copied to the temporary directory as xxx.wav

When finished, the temporary directory (aka /audio_in) contains
a directory of results:
* transcripts/txt/xxx_16kHZ.txt
* transcripts/json/xxx_16kHZ.json
which are copied to their respective output locations

For some reason the script overall is failing because somewhere in the mix
the overlay is returning -ENODATA when trying to write to the container

## run_kaldi.sh
This is the old start script and it is unused.  It does effectively the same
thing as kaldi.py, except that it always makes a 100M file and binds an input
directory directly instead of creating a tmpdir and copying files in/out of it

# Inside the container

## Lots of symlinkery
* /kaldi -> /opt/kaldi
* /usr/local/kaldi -> /opt/kaldi

## Known writable places
* /audio_in - this is bound to the input/output directory
* /audio_in_16khz - 16KHz wav files for input
* /var/extra - temporary space?
* /var/extra/audio/work - set as TMPDIR in run.sh
* /kaldi/egs/american-archive-kaldi/sample_experiment/output - 
  created by the container's run_kaldi.py to hold the below
* /kaldi/egs/american-archive-kaldi/sample_experiment/output/{json,txt} -
  created by the container's run_kaldi.py to hold the transcripts
* /kaldi/egs/american-archive-kaldi/sample_experiment/exp/make_mfcc/test -
  this is specified by run.sh as a constant to some scripts

## /usr/local/bin/start_transcription.sh 
(src: resources/setup.sh)
This is the container runscript -- it was sourced from PUA.

It's written horribly by someone who didn't know what the heck they were doing.

It looks for files with various extensions and makes 16KHz wav files out of 
them.  These wav files are in /audio_in_16khz/

For our input file of /audio_in/xxx.wav, the file generated would be
/audio_in_16khz/xxx_16kHz.wav

It then fires off 
```
/kaldi/egs/american-archive-kaldi/run_kaldi.py /kaldi/egs/american-archive-kaldi/sample_experiment/ /audio_in_16khz/ && \
rsync -a /kaldi/egs/american-archive-kaldi/sample_experiment/output/ /audio_in/transcripts/
```

which runs the transcription and then copies the files if the transcription was
successful.  It then removes all of the files in /audio_in_16khz

## /kaldi/egs/american-archive-kaldi/run_kaldi.py 
(src: resources/american-archive-kaldi/sample_experiment/run_kaldi.py)

This script takes two arguments:
1. where the kaldi experiment is stored
2. the wav input directory

It changes directory to the experiment directory (which per the 
start_transcription.sh script is 
/kaldi/egs/american-archive-kaldi/sample_experiment) and creates a few 
directories there:
* output
* output/json
* output/txt

This is where the ENODATA first appears.

For every file in the wave dir (which is /audio_in_16khz) it will generate a
json and a text file transcripts.

For the json file it is effectively calling:
```
./run.sh <wave input file> <json output file>
```
so expanded-wise, it's calling:
```
/kaldi/egs/american-archive-kaldi/sample_experiment/run.sh /audio_in_16khz/xxx_16kHz.wav output/json/xxx_16kHz.json
```
To create the text file it's running a python module called json2txt which
looks to be home built.  It converts the json file (specified as output/json/xxx_16kHz.json) to text (specified as: output/txt/xxx_16kHz.txt)

Both of these output files are rsync'd to /audio_in/transcripts by the
start_transcription.sh script

## /kaldi/egs/american-archive-kaldi/sample_experiment/run.sh 
(src: resources/american-archive-kaldi/sample_experiment/run.sh)

This is the main kaldi driver, I think.  It takes two args:
1. the wave file to work with
2. the json output file

The first thing it does is set up the paths (in set-kaldi-path.sh) so
it can find everythign:
* KALDI_ROOT=/kaldi
* THIS_DIR=.  (that's because run_kaldi.py calls this as ./run.sh)
* PATH=$THIS_DIR/:$THIS_DIR/utils:a bunch of $KALDI_ROOT things:$PATH

utils is a symlink to another kaldi thing (/opt/egs/wsj/s5/utils).  While not
specified in the path, the steps directory also symlinks to that data set
in /opt/egs/wsg/js5/steps.   The /opt/egs/wsj is a data set that used around
80 hours of sentences read from the wall street journal

NOTE: The string "wsj" doesn't appear in the utils or the steps directories
so they may be candidates for inlining to make things more understandable?  

$TMPDIR is set as /var/extra/audio/work and a $WORK directory
for the file is created at $TMPDIR/audio-tmp-$wavName-$$
That would expand to:
/var/extra/audio/work/audio-tmp-xxx_16kHz-$$

### Segmenting audio

The input file is copied to the $WORK directory 
/var/extra/audio/work/audio-tmp-xxx_16kHz-$$/xxx_16kHz.wav

there's a complicated pipeline with perl regexs that looks like
it is creating a directory if it needs to.
```
echo $wavName | perl -pe "s:^:$WORK/tmp-rec/:" | perl -pe 's:^(.*)/.*$:$1:' 
| sort -u | xargs --no-run-if-empty mkdir -p
```

What that is I don't even.  
* $wavName is just the base filename (i.e. xxx_16kHz)
* the first regex prepends the work directory to it, resulting in
  `/var/extra/audio/work/audio-tmp-xxx_16kHz-$$/tmp-rec/xxx_16kHz`
* the second regex strips off the last pathcomponent:
  `/var/extra/audio/work/audio-tmp-xxx_16kHz-$$/tmp-rec`
* the sort only shows unique entries...since there's only one here, it's useless
* the xargs will try to run a command if there's a value, so it will do
  `mkdir -p /var/extra/audio/work/audio-tmp-xxx_16kHz-$$/tmp-rec`
  which is equal to $WORK/tmp-rec.  

I guess it might be useful if wavName wasn't just the bare filename, but since
they set it up that way 16 lines prior, I'm not sure what the hell they were
thinking.

Anyway, it looks like there's a bunch of scripts that get called that all
use $WORK in their parameters.  Not going to go through them in detail unless
there's something notable.  

* wav2pem uses $TMP as it's temporary directory.  Creates 
  $WORK/tmp-rec/$wavName.pem
* sox is used to create a bunch of wav files that are chunks of the source
* the filename/duration data is written to $WORK/splitFiles.dbl

### Preparing data

$dataPrep is set to $WORK/dataPrep and is created as a directory.  There's some
data that gets written there.

Apparently the "PATH is wonky" so it changes directory to prefix (which is '.'
because we were run as "./run.sh") and some of the scripts in utils & steps are 
run.

* utils/utt2spk_to_spk2utt.pl only writes to stdout and is piped to $dataPrep
* steps/make_mfcc.sh uses $dataPrep as it's data directory, and $WORK/mfcc the
  mfcc directory, but it is passed exp/make_mfcc/test as its log directory. That
  should probably be made to use a $WORK-based path
* steps/compute_cmvn_stats.sh looks to be the same situation as above.

### Decoding

There are several decodeDir variables that are set up:
* decodeDirF=exp/tri3/decode-$wavName
    * output file for decode_fmllr.sh
    * input file for decode.sh
* decodeDir=exp/tri3_mmi_b0.1/decode-$wavName 
    * output for decode.sh
    * input for lmrestore_const_arpa.sh
* decodeDirR=exp/tri3_rescore/decode-$wavName
    * output for lmrescore_const_arpa.sh
    * input for lattice-1best

The scripts seem to be OK to use a $WORK-based pathname, but in run.sh they're
set to paths in exp, so that's bad.

### Writing output
This section already seems to be relocatable since it pulls data from $dataPrep
and $WORK and outputs to $WORK. until finally writing to $OUTPUT.


# So...what to do?

Let's reconfigure this a bit so a single bind handles all of the cases.

See AMP-2234-kaldi branch!
