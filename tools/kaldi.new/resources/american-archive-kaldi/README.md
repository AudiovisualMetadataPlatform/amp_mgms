# Pop Up Archive Kaldi release
## Prequisites
* [Kaldi] (https://github.com/kaldi-asr/kaldi)
* [SoX] (http://sox.sourceforge.net/) for audio files
* [ffmpeg] (https://www.ffmpeg.org/) for converting video files
* CMUSeg (use `sample_experiment/install-cmuseg.sh`)
* IRSTLM (use `[KALDI-PATH]/tools/extras/install_irstlm.sh`)
* sclite (see `[KALDI-PATH]/tools/sctk-2.4.10`)
* Latest version of [exp dir] (https://sourceforge.net/projects/popuparchive-kaldi/files/), should be (re-)named`exp`

##Notes about Kaldi
It is recommended that you review the [Kaldi documentation] (http://kaldi-asr.org/doc/) before you begin, especially if you intend to modify the compiled model included on Sourceforge.

## Expected Set-up
Each model you experiment with should have its own directory. Start by putting the exp dir from Sourceforge in the sample_experiment dir.
### Preliminaries for your experiment dir (e.g. sample_experiment)
* Make sure `path.sh` and `set-kaldi-path.sh` match your Kaldi location.
* Create the following sym links in your experiment dir
	* `ln -s [KALDI-PATH]/egs/wsj/s5/steps [EXPT-DIR]`
	* `ln -s [KALDI-PATH]/egs/wsj/s5/utils [EXPT-DIR]`

### Other preliminaries
* Create a directory to store results from sclite, e.g. `mkdir results`
* Convert audio to mono 16-bit Signed Integer PCM, sample rate 16K
* Example with sox `sox input.mp3 -c 1 -r 16000 -L output.wav`
* Feel free to increase `nj` and/or `decode_nj` in `exp/run.sh` depending on how much memory you have. In decoding, expect each job to use at least 5 gb. 
* If you have ground truth transcripts and wish to evaluate the accuracy of your output, create a text file in the following format:
	* The transcript for each file should be on a single line, all lower case without punctuation.
	* The line of transcript text should end with `([FILENAME]-1)`. Do not use dashes or underscores in the file name.
	* Include a new line at the end of the file.

## Usage
Run kaldi speech recognition on directory of wav files: 
`python run_kaldi.py [EXPERIMENT-DIR] [WAV-DIR]`  
Run evaluation (`[RESULTS-DIR]` will be created and sclite files will be written there):
`python run_sclite.py [KALDI-OUTPUT-DIR] [RESULTS-DIR] [REF-FILE-PATH]`

##Building on the model
You can use the current model as is, or add your own lexicon or language model.
* You can add new words to the lexicon by editing `exp/dict/lexicon.txt` and running `sh prep_lang_local.sh exp/dict exp/tmp_lang exp/lang`. Make sure your pronunciations only use phones that are already in the lexicon.
* Use `sh add_grammar.sh [LM-FILEPATH]` to create a new bigram language model based on an LM textfile and to update the overall model. Use `sh create_big_lm.sh [LM-FILEPATH] lang_newlm lang_lmrescore` to create a new 5-gram language for rescoring.
* Additional raw LM text can be obtained from [Open SLR] (http://www.openslr.org/27/). They also include trigram and 4-gram pre-trained LMs, however we recommend using a bigram baseline and 5-gram rescoring.

## Acknowledgements
This repo is based on [work] (https://github.com/APMG/audio-search) done by APM with Cantab Research.
