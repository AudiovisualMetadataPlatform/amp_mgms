shot_container.sif: \
		shot_container.recipe azure_shot_detection.py  pyscenedetect.py \
		../amp_schema/shot_detection.py ../amp_util/mgm_utils.py ../amp_util/mgm_logger.py
	singularity build --force --fakeroot shot_container.sif shot_container.recipe

install:  shot_container.sif azure_shot_detection.xml pyscenedetect.xml
	mkdir -p $(DESTDIR)/tools/amp_shot
	cp $^ $(DESTDIR)/tools/amp_shot
	