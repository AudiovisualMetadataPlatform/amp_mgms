#!/bin/bash
# Please don't blame me (bdwheele) for this script.  It's pretty much as-is from what I found at the
# american archive kaldi repo.  So very, very, wrong.

cd /audio_in/

## Now add media files to /audio_in/

for file in *.{wav,mp3,mp4,WAV,MP3,MP4}; do
if [ ${file: -4} == ".mp3" ]; then
base=$(basename """$file""" .mp3);
fi
if [ ${file: -4} == ".MP3" ]; then
base=$(basename """$file""" .MP3);
fi
if [ ${file: -4} == ".mp4" ]; then
base=$(basename """$file""" .MP4);
fi
if [ ${file: -4} == ".MP4" ]; then
base=$(basename """$file""" .MP4);
fi
if [ ${file: -4} == ".wav" ]; then
base=$(basename """$file""" .wav);
fi
if [ ${file: -4} == ".WAV" ]; then
base=$(basename """$file""" .WAV);
fi
ffmpeg -i """$file""" -ac 1 -ar 16000 """$base"""_16kHz.wav;
done

#mkdir /audio_in_16khz/
mv *_16kHz.wav /audio_in_16khz/

######### Starting the batch transcription run ##########

python /kaldi/egs/american-archive-kaldi/run_kaldi.py /kaldi/egs/american-archive-kaldi/sample_experiment/ /audio_in_16khz/ && \
rsync -a /kaldi/egs/american-archive-kaldi/sample_experiment/output/ /audio_in/transcripts/

rm -rf /audio_in_16khz/*
