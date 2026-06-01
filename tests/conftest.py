# tests/conftest.py
# Adds the project root directory to sys.path so that pvsim_engine
# can be imported from any working directory without installation.
#
# Forces matplotlib to use the non-interactive Agg backend so tests
# run cleanly in CI, headless servers, and Windows without Tcl/Tk.
import os
import sys

# Must be set before matplotlib is imported anywhere
os.environ['MPLBACKEND'] = 'Agg'

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))