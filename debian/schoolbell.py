#!/usr/bin/@PYTHON@
"""
A script to start the SchoolBell server in a Debian system.
"""

import sys
sys.path.insert(0, '/usr/share/schoolbell')
sys.path.insert(0, '/usr/lib/schooltool')

# Change the default config file name by prepending a command-line argument
sys.argv.insert(1, '--config=/etc/schoolbell/schoolbell.conf')

import schooltool.main
schooltool.main.main()
