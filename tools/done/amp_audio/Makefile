ffmpeg_container.sif: extract_audio.py remove_trailing_silence.py ffmpeg_container.recipe
	singularity build --force --fakeroot ffmpeg_container.sif ffmpeg_container.recipe

install:  ffmpeg_container.sif extract_audio.xml remove_trailing_silence.xml
	mkdir -p $(DESTDIR)/tools/amp_audio
	cp $^ $(DESTDIR)/tools/amp_audio
	