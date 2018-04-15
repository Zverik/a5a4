import os, sys, config
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, BASE_DIR)
VENV_DIR = os.path.join(BASE_DIR, 'venv', 'lib', config.PYTHON, 'site-packages')
if os.path.exists(VENV_DIR):
    sys.path.insert(1, VENV_DIR)

from app import app as application
