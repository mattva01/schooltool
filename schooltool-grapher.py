#!/usr/bin/env python2.3
#Boa:App:BoaApp

# SchoolTool - common information systems platform for school administration
# Copyright (c) 2003 Shuttleworth Foundation
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
SchoolTool database graphing tool.

This is aimed at developers, not end users.

Requires the Graphviz application
http://www.research.att.com/sw/tools/graphviz/download.html
with the "dot" application in your command path.
"""

import sys
if sys.version_info < (2, 3):
    print >> sys.stderr, '%s: need Python 2.3 or later.' % sys.argv[0]
    print >> sys.stderr, 'Your python is %s' % sys.version
    sys.exit(1)

import os
basedir = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(basedir, 'src'))

from wxPython.wx import *

import schooltool.clients.wxgraph

modules ={'graphclient': [0, '', 'src/schooltool/clients/graphclient.py'],
 'wxgraph': [1,
             'Main frame of Application',
             'src/schooltool/clients/wxgraph.py']}

class BoaApp(wxApp):
    def OnInit(self):
        wxInitAllImageHandlers()
        self.main = schooltool.clients.wxgraph.create(None)
        # needed when running from Boa under Windows 9X
        self.SetTopWindow(self.main)
        self.main.Show(); self.main.Hide(); self.main.Show()
        return True

def main():
    application = BoaApp(0)
    application.MainLoop()

if __name__ == '__main__':
    main()
