#!/usr/bin/env python2.3
"""
A script to start the schooltool GUI client from the source directory.
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

import schooltool.clients.wxclient
schooltool.clients.wxclient.main()
