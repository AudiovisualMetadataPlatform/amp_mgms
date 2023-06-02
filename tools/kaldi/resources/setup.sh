#!/bin/bash
# Original: Please don't blame me (bdwheele) for this script.  It's pretty much as-is from what I found at the
# american archive kaldi repo.  So very, very, wrong.
# New:  Yeah, you can blame me now.

# Let's make sure that anything that looks like a temporary envrionment
# variable ends up in /writable/temp!
export TMP=/writable/temp
export TMPDIR=$TMP
export TEMP=$TMP

# check for the debugging sentinel
if [ -e $TMP/.debug ]; then
    set -x
fi


# make sure that the media files are 16kHz wav
cd /writable/input
mkdir $TMP/audio_in_16kHz
for file in *; do
    for s in .wav .WAV .mp3 .MP3 .mp4 MP4; do
        if [ ${file: -4} == $s ]; then
            base=$(basename $file $s)
            ffmpeg -i $file -ac 1 -ar 16000 $TMP/audio_in_16kHz/${base}.wav;
        fi
    done
done

######### Starting the batch transcription run ##########
python /kaldi/egs/american-archive-kaldi/run_kaldi.py \
    /kaldi/egs/american-archive-kaldi/sample_experiment/ \
    $TMP/audio_in_16kHz/ 
    

# check for the shell sentinel
if [ -e $TMP/.start_shell ]; then
    echo "Starting a shell in the container"
    /bin/bash
fi