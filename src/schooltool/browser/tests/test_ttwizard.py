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
Tests for SchoolTool timetable schema wizard.

$Id$
"""

import unittest

from zope.testing import doctest
from zope.publisher.browser import TestRequest
from zope.interface import directlyProvides
from zope.app.testing import ztapi
from zope.app.traversing.interfaces import IContainmentRoot
from zope.app.component.site import LocalSiteManager
from zope.app.component.hooks import setSite
from zope.app.container.interfaces import INameChooser

from schoolbell.app.browser.tests import setup as schoolbell_setup
from schoolbell.app.app import SimpleNameChooser
from schooltool.tests import setUpApplicationPreferences
from schooltool.app import SchoolToolApplication
from schooltool.interfaces import ITimetableSchemaContainer


def setUpNameChoosers():
    """Set up name choosers.

    This particular test module is only interested in name chooser
    for ITimetableSchemaContainer.
    """
    ztapi.provideAdapter(ITimetableSchemaContainer, INameChooser,
                         SimpleNameChooser)


def setUpApplicationAndSite():
    """Set up a SchoolTool application as the active site.

    Returns the application.
    """
    app = SchoolToolApplication()
    directlyProvides(app, IContainmentRoot)
    app.setSiteManager(LocalSiteManager(app))
    setSite(app)
    return app


def setUp(test):
    """Test setup.

    Sets up enough of Zope 3 to be able to render page templates.

    Creates a SchoolTool application and makes it both the current site
    and the containment root.  The application object is available as
    a global named `app` in all doctests.
    """
    schoolbell_setup.setUp(test)
    setUpApplicationPreferences()
    setUpNameChoosers()
    test.globs['app'] = setUpApplicationAndSite()


def tearDown(test):
    """Test cleanup."""
    schoolbell_setup.tearDown(test)


def print_ttschema(ttschema):
    """Print a timetable schema as a grid."""
    for row in map(None, *[[day_id] + list(day.periods)
                           for day_id, day in ttschema.items()]):
        print " ".join(['%-10s' % cell for cell in row])


def doctest_TimetableSchemaWizard():
    """Unit test for TimetableSchemaWizard

        >>> from schooltool.browser.ttwizard import TimetableSchemaWizard
        >>> context = app['ttschemas']
        >>> request = TestRequest()
        >>> view = TimetableSchemaWizard(context, request)

        >>> print view()
        <BLANKLINE>
        ...<input class="textType" id="field.title" name="field.title"
                  size="20" type="text" value="default" />...
        ...<input type="submit" class="button-ok" name="CREATE"
                 value="Create timetable schema" />
        ...

    In its first primitive incarnation, the wizard can magically create a whole
    schema from no user data at all!  XXX: fix this

        >>> request = TestRequest(form={'field.title': u'Sample Schema',
        ...                             'CREATE': u'Create'})
        >>> view = TimetableSchemaWizard(context, request)
        >>> print view()
        <BLANKLINE>
        ...

        >>> ttschema = context['sample-schema']
        >>> ttschema
        <...TimetableSchema object at ...>
        >>> print ttschema.title
        Sample Schema

    We should get redirected to the ttschemas index:

        >>> request.response.getStatus()
        302
        >>> request.response.getHeader('Location')
        'http://127.0.0.1/ttschemas'

    """


def doctest_TimetableSchemaWizard_createSchema():
    """Unit test for TimetableSchemaWizard.createSchema

        >>> from schooltool.browser.ttwizard import TimetableSchemaWizard
        >>> context = app['ttschemas']
        >>> request = TestRequest(form={'field.title': 'Default'})
        >>> view = TimetableSchemaWizard(context, request)

        >>> ttschema = view.createSchema()
        >>> ttschema
        <...TimetableSchema object at ...>
        >>> print ttschema.title
        Default
        >>> print_ttschema(ttschema)
        Monday     Tuesday    Wednesday  Thursday   Friday
        A          A          A          A          A
        B          B          B          B          B

        >>> ttschema.model
        <...WeeklyTimetableModel object at ...>
        >>> print " ".join(ttschema.model.timetableDayIds)
        Monday Tuesday Wednesday Thursday Friday

    """


def doctest_TimetableSchemaWizard_add():
    """Unit test for TimetableSchemaWizard.createSchema

        >>> from schooltool.browser.ttwizard import TimetableSchemaWizard
        >>> context = app['ttschemas']
        >>> request = TestRequest()
        >>> view = TimetableSchemaWizard(context, request)

        >>> from schooltool.timetable import TimetableSchema
        >>> ttschema = TimetableSchema([], title="Timetable Schema")
        >>> view.add(ttschema)

        >>> context['timetable-schema'] is ttschema
        True

    """


def test_suite():
    optionflags = (doctest.ELLIPSIS | doctest.REPORT_NDIFF |
                   doctest.NORMALIZE_WHITESPACE |
                   doctest.REPORT_ONLY_FIRST_FAILURE)
    return doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
                                optionflags=optionflags)


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
