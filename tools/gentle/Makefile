gentle_forced_alignment.sif: Apptainer.recipe
	apptainer build --force --fakeroot gentle_forced_alignment.sif Apptainer.recipe

install:  gentle_forced_alignment.sif gentle_forced_alignment.py gentle_forced_alignment.xml gentle_forced_alignment_txt.py gentle_forced_alignment_txt.xml
	mkdir -p $(DESTDIR)/tools/gentle
	cp $^ $(DESTDIR)/tools/gentle
	