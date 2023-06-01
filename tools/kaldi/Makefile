Apptainer.cpu: Apptainer.in
	sed -e "s/__TAG__/latest/g" < Apptainer.in >Apptainer.cpu

Apptainer.gpu: Apptainer.in 
	sed -e "s/__TAG__/gpu-latest/g" < Apptainer.in >Apptainer.gpu

kaldi-pua-cpu.sif: Apptainer.cpu
	if [ ! -e exp2.tar.gz ] || ! sha1sum -c exp2.tar.gz.sha1 ; then \
		rm -f exp2.tar.gz; \
		curl -o exp2.tar.gz https://dlib.indiana.edu/AMP-packages/resources/exp2.tar.gz; \
	fi
	apptainer build --force --fakeroot kaldi-pua-cpu.sif Apptainer.cpu

kaldi-pua-gpu.sif: kaldi-pua-apptainer/Apptainer.gpu
	if [ ! -e exp2.tar.gz ] || ! sha1sum -c exp2.tar.gz.sha1 ; then \
		rm -f exp2.tar.gz; \
		curl -o exp2.tar.gz https://dlib.indiana.edu/AMP-packages/resources/exp2.tar.gz; \
	fi
	apptainer build --force --fakeroot kaldi-pua-gpu.sif Apptainer.gpu


# Kaldi's GPU verison doesn't seem to be building -- skip it.
#install:  kaldi-pua-cpu.sif kaldi-pua-gpu.sif kaldi.py kaldi.xml kaldi_transcript_to_amp_transcript.py
install:  kaldi-pua-cpu.sif kaldi.py kaldi.xml kaldi_transcript_to_amp_transcript.py
	mkdir -p $(DESTDIR)/tools/kaldi
	cp $^ $(DESTDIR)/tools/kaldi
	