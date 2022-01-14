segment_container.sif: \
		segment_container.recipe adjust_diarization_timestamps.py adjust_transcript_timestamps.py \
		applause_detection_to_avalon_xml.py keep_speech.py adjustment.py applause_detection.py \
		ina_speech_segmenter.py remove_silence_music_speech.py \
		../amp_schema/speech_to_text.py ../amp_schema/segmentation.py ../amp_util/mgm_utils.py ../amp_util/mgm_logger.py
	singularity build --force --fakeroot segment_container.sif segment_container.recipe

install:  segment_container.sif adjust_diarization_timestamps.xml applause_detection_to_avalon_xml.xml \
          ina_speech_segmenter.xml remove_silence_speech.xml adjust_transcript_timestamps.xml applause_detection.xml \
		  keep_speech.xml
	mkdir -p $(DESTDIR)/tools/amp_segment
	cp $^ $(DESTDIR)/tools/amp_segment
	