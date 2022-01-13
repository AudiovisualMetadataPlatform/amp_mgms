dlib_face_recognition.sif: dlib_face_recognition.py dlib_face_training.py dlib_face_recognition.recipe \
	  					   ../amp_util/mgm_logger.py ../amp_util/mgm_utils.py ../amp_schema/facial_recognition.py
	singularity build --force --fakeroot dlib_face_recognition.sif dlib_face_recognition.recipe

install:  dlib_face_recognition.sif dlib_face_recognition.xml
	mkdir -p $(DESTDIR)/tools/amp_facial
	cp $^ $(DESTDIR)/tools/amp_facial
	
