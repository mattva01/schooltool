"""
This module lets schoolbell know where its data files are installed.

XXX -   This is not connected up to the reast of schoolbell, and may never be.
        If it is not, theis file should eventually be removed and the ugly
        hacks in setup.py made permanent.
"""
import os

# pathconf begin
DATADIR = os.path.dirname(__file__)
# pathconf end
