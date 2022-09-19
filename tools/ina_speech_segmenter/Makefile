ina_speech_segmenter.sif: ina-speech-tools-singularity/Singularity.recipe
	cd ina-speech-tools-singularity && singularity build --force --fakeroot ../ina_speech_segmenter.sif Singularity.recipe

install:  ina_speech_segmenter.sif ina_speech_segmenter.py ina_speech_segmenter.xml
	mkdir -p $(DESTDIR)/tools/ina_speech_segmenter
	cp $^ $(DESTDIR)/tools/ina_speech_segmenter
	