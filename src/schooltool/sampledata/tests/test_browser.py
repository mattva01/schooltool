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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
Unit tests for schooltool.sampledata.generator
"""
import unittest
import doctest
from pprint import pprint

from zope.app.testing import setup
from zope.publisher.browser import TestRequest
from zope.component import provideUtility
from schooltool.testing.setup import setUpSchoolToolSite
from schooltool.testing.setup import setUpApplicationPreferences
import schooltool.app.browser.testing

def setUp(test):
    setup.placefulSetUp()


def tearDown(test):
    setup.placefulTearDown()


def doctest_SampleDataView_update():
    """Tests for SampleDataView.update method

        >>> app = setUpSchoolToolSite()

    When seed is not provided in the request, the seed is set to
    'SchoolTool', so that sample data is reproducible:

        >>> from schooltool.sampledata.browser import SampleDataView
        >>> request = TestRequest()
        >>> view = SampleDataView(app, request)
        >>> view.update()
        >>> view.seed
        'SchoolTool'

    Otherwise update picks up the seed value:

        >>> request = TestRequest(form={'seed': 'random-data-123'})
        >>> view = SampleDataView(app, request)
        >>> view.update()
        >>> view.seed
        'random-data-123'

    If the seed is an empty string, the seed value is None, so that
    the random number generators initialize from current time.

        >>> request = TestRequest(form={'seed': ''})
        >>> view = SampleDataView(app, request)
        >>> view.update()
        >>> view.seed

    Now, let's set up some stub sample data plugins.

        >>> from schooltool.sampledata.tests.test_generator import DummyPlugin
        >>> from schooltool.sampledata.interfaces import ISampleDataPlugin
        >>> p1 = DummyPlugin("work.day", ())
        >>> p2 = DummyPlugin("play", ("work.day", ))
        >>> provideUtility(p1, ISampleDataPlugin, 'work.day')
        >>> provideUtility(p2, ISampleDataPlugin, 'play')

    If we fill in the seed and press the submit button, we get sample
    data plugins called.

        >>> DummyPlugin.log = []
        >>> request = TestRequest(form={'seed': 'data', 'SUBMIT': 'Generate',
        ...                             'plugin.work.day': 'checked',
        ...                             'plugin.play': 'checked'})
        >>> view = SampleDataView(app, request)
        >>> view.update()
        >>> pprint(DummyPlugin.log)
        [('work.day',
          <schooltool.app.app.SchoolToolApplication object at ...>,
          'data'),
         ('play',
          <schooltool.app.app.SchoolToolApplication object at ...>,
          'data')]

    When the work is done the times attribute is set on the view:

        >>> sorted(view.times)
        ['play', 'work.day']
        >>> for item, time in view.times.items():
        ...     assert time < 0.1   # 100 ms ought to be enough to do nothing
        >>> view.work_done
        True

    If we press the cancel button, we also get redirected to the main page:

        >>> request = TestRequest(form={'seed': 'data', 'CANCEL': 'Cancel'})
        >>> view = SampleDataView(app, request)
        >>> view.update()
        >>> request.response.getStatus()
        302
        >>> request.response.getHeader('location')
        'http://127.0.0.1'

    Clean up:

        >>> DummyPlugin.log = []
    """

def doctest_SampleDataView__call__():
    """Tests for SampleDataView rendering

    We'll need a massive browser views setup here.

        >>> schooltool.app.browser.testing.setUp()
        >>> setUpApplicationPreferences()

    Let's set up some plugins so they are called:

        >>> from schooltool.sampledata.tests.test_generator import DummyPlugin
        >>> from schooltool.sampledata.interfaces import ISampleDataPlugin
        >>> p1 = DummyPlugin("work.day", ())
        >>> p2 = DummyPlugin("play", ("work.day", ))
        >>> provideUtility(p1, ISampleDataPlugin, 'work.day')
        >>> provideUtility(p2, ISampleDataPlugin, 'play')

    Let's create an application object and a view:

        >>> from schooltool.sampledata.browser import SampleDataView
        >>> app = setUpSchoolToolSite()
        >>> request = TestRequest(form={'seed': 'test'})
        >>> view = SampleDataView(app, request)

    Let's render the view.  The default value of the seed is displayed there.

        >>> print view()
        <BLANKLINE>
        ...
        <h1>Sample Data Generation</h1>
        ...
        <form method="POST" class="standalone"
              action="http://127.0.0.1">
          <div class="row">
            <div class="label">
               <label>Random seed</label>
            </div>
            <div class="field">
               <input name="seed" value="test" />
            </div>
          </div>
          <fieldset>
            <legend>Plugins</legend>
            <div class="item_list">
            <div>
              <label>
                <input type="checkbox" name="plugin.play" />
                play
              </label>
            </div>
            <div>
              <label>
                <input type="checkbox" name="plugin.work.day" />
                work.day
              </label>
            </div>
            <div class="controls">
              <input type="submit" class="button-ok"
                     name="DEPENDENCIES" value="View Dependencies" />
              <input type="submit" class="button-ok" name="CLEAR"
                     value="Clear" />
            </div>
          </div></fieldset>
          <div class="controls">
            <input type="submit" class="button-ok" name="SUBMIT"
                   value="Generate" />
            <input type="submit" class="button-cancel" name="CANCEL"
                   value="Cancel" />
          </div>
        </form>
        ...

    Let's render the view.  The default value of the seed is displayed there.

        >>> request = TestRequest(form={'seed': 'test', 'SUBMIT': 'Generate',
        ...                             'plugin.work.day': 'checked',
        ...                             'plugin.play': 'checked'})
        >>> view = SampleDataView(app, request)
        >>> print view()
        <BLANKLINE>
        ...
        <p>Sample data generated.  Below is the list of plugins executed along
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
            <td>work.day</td>
            <td>...</td>
          </tr>
        </table>
        ...
    """

def doctest_SampleDataView_work_done():
    """Tests for SampleDataView.work_done propery.

        >>> from schooltool.sampledata.browser import SampleDataView
        >>> request = TestRequest()
        >>> view = SampleDataView(object(), request)

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
