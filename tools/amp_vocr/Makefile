vocr_container.sif: \
		vocr_container.recipe azure_video_ocr.py tesseract.py vocr_to_csv.py \
		../amp_schema/video_ocr.py ../amp_util/mgm_utils.py ../amp_util/mgm_logger.py
	singularity build --force --fakeroot vocr_container.sif vocr_container.recipe

install:  vocr_container.sif azure_video_ocr.xml tesseract.xml vocr_to_csv.xml
	mkdir -p $(DESTDIR)/tools/amp_vocr
	cp $^ $(DESTDIR)/tools/amp_vocr
	