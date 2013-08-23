#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2011 Shuttleworth Foundation
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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
Selenium functional tests for schooltool.app.app
"""
import os
import unittest

from schooltool.app.testing import app_selenium_layer
from schooltool.app.testing import app_selenium_oldskin_layer
from schooltool.testing.selenium import collect_ftests


testdir = os.path.dirname(__file__)
oldskin = ('app.txt',)
stests = [fn for fn in os.listdir(testdir)
          if (fn.endswith('.txt') and
              not fn.startswith('.') and
              not fn in oldskin)]


def test_suite():
    return unittest.TestSuite([
        collect_ftests(layer=app_selenium_layer, filenames=stests),
        collect_ftests(layer=app_selenium_oldskin_layer, filenames=oldskin),
        ])


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
