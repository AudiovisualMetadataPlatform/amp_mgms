mgm_python.sif: mgm_python.recipe 
	singularity build --force --fakeroot mgm_python.sif mgm_python.recipe

install:  mgm_python.sif 
	mkdir -p $(DESTDIR)/tools/amp_mgms
	cp $^ $(DESTDIR)/tools/amp_mgms
	