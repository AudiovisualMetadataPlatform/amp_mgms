video_container.sif: \
		video_container.recipe azure_video_indexer.py contact_sheets_collection.py contact_sheets.py \
		../amp_schema/contact_sheet.py
	singularity build --force --fakeroot video_container.sif video_container.recipe

install:  video_container.sif azure_video_indexer.xml contact_sheets_collection.xml contact_sheets.xml
	mkdir -p $(DESTDIR)/tools/amp_video
	cp $^ $(DESTDIR)/tools/amp_video
	