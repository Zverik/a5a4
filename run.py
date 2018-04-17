#!/usr/bin/env python3
import os
import sys
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, BASE_DIR)
python_dir = [n for n in os.listdir(os.path.join(BASE_DIR, 'venv', 'lib')) if n.startswith('python')][0]
VENV_DIR = os.path.join(BASE_DIR, 'venv', 'lib', python_dir, 'site-packages')
if os.path.exists(VENV_DIR):
    sys.path.insert(1, VENV_DIR)

from app import app
app.run(debug=True)
