applause_detection.sif: applause-detection/applause-detection.def applause-detection/requirements.txt
	cd applause-detection && singularity build --force --fakeroot ../applause_detection.sif applause-detection.def

install:  applause_detection.sif applause_detection.py applause_detection.xml
	mkdir -p $(DESTDIR)/tools/applause_detection
	cp $^ $(DESTDIR)/tools/applause_detection
	