#!/usr/bin/@PYTHON@
"""
A script to start the SchoolTool server in a Debian system.
"""

import sys
sys.path.insert(0, '/usr/share/schooltool')
sys.path.insert(0, '/usr/lib/schooltool')

# Change the default config file name by prepending a command-line argument
sys.argv.insert(1, '--config=/etc/schooltool/schooltool.conf')

import schooltool.main
schooltool.main.main()
