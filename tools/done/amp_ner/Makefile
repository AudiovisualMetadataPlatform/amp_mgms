ner_container.sif: \
		ner_container.recipe aws_comprehend.py  ner_helper.py  ner_to_csv_.py  spacy_.py \
		../amp_schema/entity_extraction.py ../amp_schema/speech_to_text.py ../amp_util/mgm_utils.py ../amp_util/mgm_logger.py
	singularity build --force --fakeroot ner_container.sif ner_container.recipe

install:  ner_container.sif aws_comprehend.xml ner_to_csv.xml spacy.xml
	mkdir -p $(DESTDIR)/tools/amp_ner
	cp $^ $(DESTDIR)/tools/amp_ner
	