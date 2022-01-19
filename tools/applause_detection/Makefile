applause_detection.sif: applause-detection/applause-detection.def
	cd applause-detection && singularity build --force --fakeroot ../applause_detection.sif applause-detection.def

install:  applause_detection.sif applause_detection.py applause_detection.xml
	mkdir -p $(DESTDIR)/tools/amp_mgms
	cp $^ $(DESTDIR)/tools/amp_mgms
	