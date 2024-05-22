ina_speech_segmenter.sif: singularity-ina-speech-tools/Singularity.recipe
	cd singularity-ina-speech-tools && apptainer build --force --fakeroot ../ina_speech_segmenter.sif Singularity.recipe

install:  ina_speech_segmenter.sif ina_speech_segmenter.py ina_speech_segmenter.xml
	mkdir -p $(DESTDIR)/tools/ina_speech_segmenter
	cp $^ $(DESTDIR)/tools/ina_speech_segmenter
	