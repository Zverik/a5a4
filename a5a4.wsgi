import sys
sys.path.insert(0, '/path/to/a5a4')
import logging
logging.basicConfig(stream=sys.stderr)
from app import app as application
