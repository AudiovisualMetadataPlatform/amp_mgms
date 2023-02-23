gentle_forced_alignment.sif: Singularity.recipe
	singularity build --force --fakeroot gentle_forced_alignment.sif Singularity.recipe

install:  gentle_forced_alignment.sif gentle_forced_alignment.py gentle_forced_alignment.xml gentle_forced_alignment_txt.py gentle_forced_alignment_txt.xml
	mkdir -p $(DESTDIR)/tools/amp_mgms
	cp $^ $(DESTDIR)/tools/amp_mgms
	