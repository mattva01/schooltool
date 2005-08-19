#!/usr/bin/env python
"""
A script to start the schoolbell server from the source directory.
"""

import sys
import os.path

if sys.version_info < (2, 3):
    print >> sys.stderr, '%s: need Python 2.3 or later.' % sys.argv[0]
    print >> sys.stderr, 'Your python is %s' % sys.version
    sys.exit(1)

# find the schoolbell config file if it exists
dirname = os.path.dirname(__file__)
config_file = os.path.join(dirname, 'schoolbell.conf')
if not os.path.exists(config_file):
    config_file = os.path.join(dirname, 'schoolbell.conf.in')

# Change the default config file name by prepending a command-line argument
sys.argv.insert(1, '--config=' + config_file)

import os
basedir = os.path.abspath(os.path.dirname(sys.argv[0]))
sys.path.insert(0, os.path.join(basedir, 'src'))
sys.path.insert(0, os.path.join(basedir, 'Zope3', 'src'))

import schooltool.sbapp.main
schooltool.sbapp.main.StandaloneServer().main()
