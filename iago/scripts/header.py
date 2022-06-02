""" django setup for iago scripts """
import sys
from pathlib import Path
import os

# Turn off bytecode generation
sys.dont_write_bytecode = True
sys.path.append(str(Path(__file__).parent.parent.absolute()))


import django
from iago.settings import DEBUG

# setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'iago.settings')
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
django.setup()
