# tests/conftest.py
# Adds the project root directory to sys.path so that pvsim_engine
# can be imported from any working directory without installation.
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))