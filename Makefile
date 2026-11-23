all:
		cd $${CI_PROJECT_DIR:-$$PWD} && rc_upload.py -V $$RC_SITE_ID $$RC_USER $$RC_PW $(DST)
