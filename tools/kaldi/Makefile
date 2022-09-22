Singularity.cpu: Singularity.in
	sed -e "s/__TAG__/latest/g" < Singularity.in >Singularity.cpu

Singularity.gpu: Singularity.in 
	sed -e "s/__TAG__/gpu-latest/g" < Singularity.in >Singularity.gpu

kaldi-pua-cpu.sif: Singularity.cpu
	if [ ! -e exp2.tar.gz ] || ! sha1sum -c exp2.tar.gz.sha1 ; then \
		rm -f exp2.tar.gz; \
		curl -o exp2.tar.gz https://dlib.indiana.edu/AMP-packages/resources/exp2.tar.gz; \
	fi
	singularity build --force --fakeroot kaldi-pua-cpu.sif Singularity.cpu

kaldi-pua-gpu.sif: kaldi-pua-singularity/Singularity.gpu
	if [ ! -e exp2.tar.gz ] || ! sha1sum -c exp2.tar.gz.sha1 ; then \
		rm -f exp2.tar.gz; \
		curl -o exp2.tar.gz https://dlib.indiana.edu/AMP-packages/resources/exp2.tar.gz; \
	fi
	singularity build --force --fakeroot kaldi-pua-gpu.sif Singularity.gpu


# Kaldi's GPU verison doesn't seem to be building -- skip it.
#install:  kaldi-pua-cpu.sif kaldi-pua-gpu.sif kaldi.py kaldi.xml kaldi_transcript_to_amp_transcript.py
install:  kaldi-pua-cpu.sif kaldi.py kaldi.xml kaldi_transcript_to_amp_transcript.py
	mkdir -p $(DESTDIR)/tools/kaldi
	cp $^ $(DESTDIR)/tools/kaldi
	