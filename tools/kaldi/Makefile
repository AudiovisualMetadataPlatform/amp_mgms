kaldi-pua-singularity/exp2.tar.gz:
	cd kaldi-pua-singularity && if [ ! -e exp2.tar.gz ] || ! sha1sum -c exp2.tar.gz.sha1 ; then rm -f exp2.tar.gz ; wget https://master.dl.sourceforge.net/project/popuparchive-kaldi/exp2.tar.gz ; fi

kaldi-pua-singularity/Singularity.cpu: kaldi-pua-singularity/Singularity.in kaldi-pua-singularity/exp2.tar.gz
	cd kaldi-pua-singularity && sed -e "s/__TAG__/latest/g" < Singularity.in >Singularity.cpu

kaldi-pua-singularity/Singularity.gpu: kaldi-pua-singularity/Singularity.in kaldi-pua-singularity/exp2.tar.gz
	cd kaldi-pua-singularity && sed -e "s/__TAG__/gpu-latest/g" < Singularity.in >Singularity.gpu

kaldi-pua-cpu.sif: kaldi-pua-singularity/Singularity.cpu
	cd kaldi-pua-singularity && singularity build --force --fakeroot ../kaldi-pua-cpu.sif Singularity.cpu

kaldi-pua-gpu.sif: kaldi-pua-singularity/Singularity.gpu
	cd kaldi-pua-singularity && singularity build --force --fakeroot ../kaldi-pua-gpu.sif Singularity.gpu

# Temporarily disable GPU build since we don't use it and
# it doesn't seem to be building right now.
#install:  kaldi-pua-cpu.sif kaldi-pua-gpu.sif kaldi.py kaldi.xml kaldi_transcript_to_amp_transcript.py
install: kaldi-pua-cpu.sif kaldi.py kaldi.xml kaldi_transcript_to_amp_transcript.py
	mkdir -p $(DESTDIR)/tools/amp_mgms
	cp $^ $(DESTDIR)/tools/amp_mgms
	