#!/usr/bin/python2.3
"""
A script to start the schooltool server in a Debian system.
"""

import sys
sys.path.insert(0, '/usr/share/schooltool-server')

# Change the default config file name by prepending a command-line argument
sys.argv.insert(1, '--config=/etc/schooltool.conf')

import schooltool.main
schooltool.main.main()
