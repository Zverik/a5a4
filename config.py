import os
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
PYTHON = 'python3.6'

DEBUG = False

MAX_CONTENT_LENGTH = 10*1024*1024
A5A4_MAXFILES = 5
A5A4_MAXPAGES = 12

# paths
IDENTIFY = '/usr/bin/identify'
CONVERT = '/usr/bin/convert'
PDFTK = '/usr/bin/pdftk'
PDFTK_NEW = False  # True for 1.45+
PDFJAM = '/usr/bin/pdfjam'

# Fill these in config_local.py
A5A4_TASKS = ''
A5A4_PASSWORD = ''
SECRET_KEY = 'whatever'

try:
    from config_local import *
except ImportError:
    pass
