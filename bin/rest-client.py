#!/usr/bin/env python
"""
A script to run the SchoolTool REST client from the source directory.
"""

import sys
import os.path

if sys.version_info < (2, 3):
    print >> sys.stderr, '%s: need Python 2.3 or later.' % sys.argv[0]
    print >> sys.stderr, 'Your python is %s' % sys.version
    sys.exit(1)


import os
basedir = os.path.normpath(os.path.join(os.path.dirname(__file__),
                                        os.path.pardir))
sys.path.insert(0, os.path.join(basedir, 'src'))
sys.path.insert(0, os.path.join(basedir, 'Zope3', 'src'))

import schooltool.client
schooltool.client.main()
