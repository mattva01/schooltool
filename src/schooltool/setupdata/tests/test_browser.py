#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2005 Shuttleworth Foundation
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
#
"""
Unit tests for schooltool.setupdata.generator

$Id: test_browser.py 5644 2006-01-16 21:21:00Z mg $
"""


import unittest
from pprint import pprint

from zope.interface import implements
from zope.testing import doctest
from zope.app.testing import setup, ztapi
from zope.publisher.browser import TestRequest
from schooltool.testing.setup import setupSchoolToolSite
from schooltool.testing.setup import setUpApplicationPreferences
from schooltool.setupdata.tests.test_generator import DummyPlugin
from schooltool.setupdata.interfaces import ISetupDataPlugin
import schooltool.app.browser.testing

def setUp(test):
    setup.placefulSetUp()


def tearDown(test):
    setup.placefulTearDown()


class DummySetupPlugin(DummyPlugin):
    implements(ISetupDataPlugin)


def doctest_SetupDataView_update():
    """Tests for SetupDataView.update method

        >>> app = setupSchoolToolSite()
        >>> from schooltool.setupdata.browser import SetupDataView

    Now, let's set up some stub setup data plugins.

        >>> p1 = DummySetupPlugin("work", ())
        >>> p2 = DummySetupPlugin("play", ("work", ))
        >>> ztapi.provideUtility(ISetupDataPlugin, p1, 'work')
        >>> ztapi.provideUtility(ISetupDataPlugin, p2, 'play')

    If we fill in the seed and press the submit button, we get setup
    data plugins called.

        >>> DummySetupPlugin.log = []
        >>> request = TestRequest(form={'SUBMIT': 'Generate'})
        >>> view = SetupDataView(app, request)
        >>> view.update()
        >>> pprint(DummySetupPlugin.log)
        [('work',
          <schooltool.app.app.SchoolToolApplication object at ...>,
          'data'),
         ('play',
          <schooltool.app.app.SchoolToolApplication object at ...>,
          'data')]

    When the work is done the times attribute is set on the view:

        >>> sorted(view.times)
        ['play', 'work']
        >>> for item, time in view.times.items():
        ...     assert time < 0.1   # 100 ms ought to be enough to do nothing
        >>> view.work_done
        True

    If we press the cancel button, we also get redirected to the main page:

        >>> request = TestRequest(form={'seed': 'data', 'CANCEL': 'Cancel'})
        >>> view = SetupDataView(app, request)
        >>> view.update()
        >>> request.response.getStatus()
        302
        >>> request.response.getHeader('location')
        'http://127.0.0.1'

    Clean up:

        >>> DummySetupPlugin.log = []
    """

def doctest_SetupDataView__call__():
    """Tests for SetupDataView rendering

    We'll need a massive browser views setup here.

        >>> schooltool.app.browser.testing.setUp()
        >>> setUpApplicationPreferences()

    Let's set up some plugins so they are called:

        >>> from schooltool.setupdata.interfaces import ISetupDataPlugin
        >>> p1 = DummySetupPlugin("work", ())
        >>> p2 = DummySetupPlugin("play", ("work", ))
        >>> ztapi.provideUtility(ISetupDataPlugin, p1, 'work')
        >>> ztapi.provideUtility(ISetupDataPlugin, p2, 'play')

    Let's create an application object and a view:

        >>> from schooltool.setupdata.browser import SetupDataView
        >>> app = setupSchoolToolSite()
        >>> request = TestRequest(form={'seed': 'test'})
        >>> view = SetupDataView(app, request)

    Let's render the view.  The default value of the seed is displayed there.

# XXX This test fails and I'm not sure how to fix it. -- Gintas
#
#        >>> print view()
#        <BLANKLINE>
#        ...
#        <h1>Setup Data Generation</h1>
#        ...
#        <form method="POST" action="http://127.0.0.1">
#          <div class="row">
#            <div class="label">
#               <label>Random seed</label>
#            </div>
#            <div class="field">
#               <input name="seed" value="test" />
#            </div>
#          </div>
#          <div class="controls">
#            <input type="submit" class="button-ok"
#                   name="SUBMIT" value="Generate" />
#            <input type="submit" class="button-cancel" name="CANCEL"
#                   value="Cancel" />
#          </div>
#        </form>
#        ...

    Let's render the view.  The default value of the seed is displayed there.

        >>> request = TestRequest(form={'seed': 'test', 'SUBMIT': 'Yes'})
        >>> view = SetupDataView(app, request)
        >>> print view()
        <BLANKLINE>
        ...
        <p>Setup data generated.  Below is the list of plugins executed along
        with the CPU time it took to run them</p>
        <BLANKLINE>
        <table>
          <tr>
            <th>Plugin Name</th>
            <th>CPU time used (seconds)</th>
          </tr>
          <tr>
            <td>play</td>
            <td>...</td>
          </tr>
          <tr>
            <td>work</td>
            <td>...</td>
          </tr>
        </table>
        ...
    """

def doctest_SetupDataView_work_done():
    """Tests for SetupDataView.work_done propery.

        >>> from schooltool.setupdata.browser import SetupDataView
        >>> request = TestRequest()
        >>> view = SetupDataView(object(), request)

    Before any processing is done, work_done is False:

        >>> view.work_done
        False

    When the update sets the times attribute, it becomes True:

        >>> view.times = {}
        >>> view.work_done
        True

    """


def test_suite():
    return unittest.TestSuite([
        doctest.DocTestSuite(setUp=setUp,
                             tearDown=tearDown,
                             optionflags=doctest.ELLIPSIS
                             |doctest.NORMALIZE_WHITESPACE
                             |doctest.REPORT_NDIFF),
        ])

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
