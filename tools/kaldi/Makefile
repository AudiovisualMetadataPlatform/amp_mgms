exp2.tar.gz:
	if [ ! -e exp2.tar.gz ] || ! sha1sum -c exp2.tar.gz.sha1 ; then rm -f exp2.tar.gz ; wget https://master.dl.sourceforge.net/project/popuparchive-kaldi/exp2.tar.gz ; fi

Singularity.cpu: Singularity.in exp2.tar.gz
	sed -e "s/__TAG__/latest/g" < Singularity.in >Singularity.cpu

Singularity.gpu: Singularity.in exp2.tar.gz
	sed -e "s/__TAG__/gpu-latest/g" < Singularity.in >Singularity.gpu

kaldi-pua-cpu.sif: Singularity.cpu
	singularity build --force --fakeroot kaldi-pua-cpu.sif Singularity.cpu

kaldi-pua-gpu.sif: kaldi-pua-singularity/Singularity.gpu
	singularity build --force --fakeroot kaldi-pua-gpu.sif Singularity.gpu


# Kaldi's GPU verison doesn't seem to be building -- skip it.
#install:  kaldi-pua-cpu.sif kaldi-pua-gpu.sif kaldi.py kaldi.xml kaldi_transcript_to_amp_transcript.py
install:  kaldi-pua-cpu.sif kaldi.py kaldi.xml kaldi_transcript_to_amp_transcript.py
	mkdir -p $(DESTDIR)/tools/amp_mgms
	cp $^ $(DESTDIR)/tools/amp_mgms
	