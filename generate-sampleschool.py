#!/usr/bin/env python
"""
A script to generate sample school data.
"""

import sys
if sys.version_info < (2, 3):
    print >> sys.stderr, '%s: need Python 2.3 or later.' % sys.argv[0]
    print >> sys.stderr, 'Your python is %s' % sys.version
    sys.exit(1)

import os
basedir = os.path.abspath(os.path.dirname(sys.argv[0]))
sys.path.insert(0, os.path.join(basedir, 'src'))
sys.path.insert(0, os.path.join(basedir, 'Zope3', 'src'))

import schooltool.clients.datagen
# If you change the seed, you will also have to recreate ttconfig.data
seed = 'schooltool-m4'
schooltool.clients.datagen.main(['datagen', seed])
