#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2008 Shuttleworth Foundation
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
Tests for School year views
"""
import unittest
import doctest
from datetime import date

from zope.interface import directlyProvides
from zope.publisher.browser import TestRequest

from schooltool.term.term import Term
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.skin.skin import ISchoolToolSkin
from schooltool.schoolyear.schoolyear import SchoolYear
from schooltool.schoolyear.browser.schoolyear import SchoolYearContainerAbsoluteURLAdapter
from schooltool.schoolyear.browser.schoolyear import SchoolYearEditView
from schooltool.schoolyear.browser.schoolyear import SchoolYearAddView
from schooltool.schoolyear.interfaces import ISchoolYearContainer
from schooltool.schoolyear.testing import setUp
from schooltool.schoolyear.testing import tearDown
from schooltool.schoolyear.testing import provideStubUtility
from schooltool.schoolyear.testing import provideStubAdapter

from schooltool.schoolyear.ftesting import schoolyear_functional_layer


def doctest_SchoolYearContainerAbsoluteURLAdapter():
    """Test for absolute url adapter for school year container.

    School year container url is fixed and does not depend on the
    __name__ of the container:

        >>> syc = ISchoolYearContainer(ISchoolToolApplication(None))
        >>> str(SchoolYearContainerAbsoluteURLAdapter(syc, TestRequest()))
        'http://127.0.0.1/schoolyears'

    """


def doctest_SchoolYearAddView():
    """Tests for school year add view.

    Let's get the school year container and a request:

        >>> app = ISchoolToolApplication(None)
        >>> syc = ISchoolYearContainer(app)
        >>> request = TestRequest()
        >>> directlyProvides(request, [ISchoolToolSkin])

    Fill in the form

        >>> request.form = {'form.buttons.add'  : u'Add',
        ...                 'form.widgets.title': u'2005-2006',
        ...                 'form.widgets.first': u'2005-09-01',
        ...                 'form.widgets.last' : u'2006-07-15'}

    And add the school year

        >>> view = SchoolYearAddView(syc, request)
        >>> view.update()

        >>> view.widgets.errors
        ()

        >>> sy = syc['2005-2006']

        >>> sy.title, sy.first, sy.last
        (u'2005-2006', datetime.date(2005, 9, 1), datetime.date(2006, 7, 15))

    If we fill in the form, but click cancel - we get redirected back
    to the school year container view:

        >>> request.form = {'form.buttons.cancel'  : u'Cancel',
        ...                 'form.widgets.title': u'',
        ...                 'form.widgets.first': u'2005-09-01',
        ...                 'form.widgets.last' : u'2006-07-15'}
        >>> view = SchoolYearAddView(syc, request)
        >>> view.update()

        >>> view.request.response.getStatus()
        302
        >>> view.request.response.getHeader('Location')
        'http://127.0.0.1/schoolyears'

    """


def doctest_SchoolYearAddView_overlap():
    """Test for school year add view overlapping school year handling.

    We get the school year container

        >>> app = ISchoolToolApplication(None)
        >>> syc = ISchoolYearContainer(app)

    Add one school year to it

        >>> syc['2005-2006'] = SchoolYear("2005-2006",
        ...                               date(2005, 9, 1),
        ...                               date(2006, 7, 16))

    Fill in the form by providing a date range that overlaps the
    existing school year:

        >>> request = TestRequest()
        >>> directlyProvides(request, [ISchoolToolSkin])
        >>> request.form = {'form.buttons.add'  : u'Add',
        ...                 'form.widgets.title': u'2006-2007',
        ...                 'form.widgets.first': u'2006-07-15',
        ...                 'form.widgets.last' : u'2007-07-15'}

    And submit it

        >>> view = SchoolYearAddView(syc, request)
        >>> view.update()

    An error message should be displayed:

        >>> for error in view.widgets.errors: print error.render()
        <div class="error">
        Date range you have selected overlaps with the following school years:
        <div> <a href="http://127.0.0.1/schoolyears/2005-2006">2005-2006</a> (2005-09-01 &mdash; 2006-07-16) </div>
        </div>

    There still should be only one school year in the container:

        >>> list(syc.keys())
        [u'2005-2006']

    """


def doctest_SchoolYearEditView():
    """Tests for school year edit view.

    Let's get the school year container:

        >>> app = ISchoolToolApplication(None)
        >>> syc = ISchoolYearContainer(app)

    Add a school year:

        >>> sy = syc['2005-2006'] = SchoolYear("2005-2006",
        ...                               date(2005, 9, 1),
        ...                               date(2006, 7, 16))

    Fill in the form

        >>> request = TestRequest()
        >>> directlyProvides(request, [ISchoolToolSkin])
        >>> request.form = {'form.buttons.apply'  : u'Apply',
        ...                 'form.widgets.title': u'2006-2007',
        ...                 'form.widgets.first': u'2006-07-15',
        ...                 'form.widgets.last' : u'2007-07-15'}

    And submit it

        >>> view = SchoolYearEditView(sy, request)
        >>> view.update()

        >>> view.widgets.errors
        ()

    The school year got updated successfully:

        >>> sy.title, sy.first, sy.last
        (u'2006-2007', datetime.date(2006, 7, 15), datetime.date(2007, 7, 15))

        >>> view.status
        u'Data successfully updated.'

    We could have just canceled though

        >>> request.form = {'form.buttons.cancel': u'Cancel',
        ...                 'form.widgets.title' : u'',
        ...                 'form.widgets.first' : u'2005-09-01',
        ...                 'form.widgets.last'  : u'2006-07-15'}

    So we'd get redirected back to the container view:

        >>> view = SchoolYearEditView(sy, request)
        >>> view.update()

        >>> view.request.response.getStatus()
        302
        >>> view.request.response.getHeader('Location')
        'http://127.0.0.1/schoolyears/2005-2006'

    """


def doctest_SchoolYearEditView_shrink():
    """Test for school year editing view terms not fitting into school year.

    We get the school year container:

        >>> app = ISchoolToolApplication(None)
        >>> syc = ISchoolYearContainer(app)

    Add a school year

        >>> sy = syc['2005-2006'] = SchoolYear("2005-2006",
        ...                               date(2005, 9, 1),
        ...                               date(2006, 7, 16))

    Two terms

        >>> sy['fall'] = Term("Fall", date(2005, 9, 1), date(2006, 1, 13))
        >>> sy['spring'] = Term("Spring", date(2006, 1, 14), date(2006, 7, 16))

    Fill in the form setting new date range so one of the terms would
    not fit into the school year anymore:

        >>> request = TestRequest()
        >>> directlyProvides(request, [ISchoolToolSkin])
        >>> request.form = {'form.buttons.apply': u'Apply',
        ...                 'form.widgets.title': u'2006-2007',
        ...                 'form.widgets.first': u'2005-09-01',
        ...                 'form.widgets.last' : u'2006-07-15'}

    Then we submit the form

        >>> view = SchoolYearEditView(sy, request)
        >>> view.update()

    And get the error message displayed

        >>> for error in view.widgets.errors: print error.render()
        <div class="error">
        Date range you have selected is too small to contain the following term(s):
        <div> <a href="http://127.0.0.1/schoolyears/2005-2006/spring">Spring</a> (2006-01-14 &mdash; 2006-07-16) </div>
        </div>

    The school year should not get modified

        >>> sy.title, sy.first, sy.last
        ('2005-2006', datetime.date(2005, 9, 1), datetime.date(2006, 7, 16))

    """


def doctest_SchoolYearEditView_overlap():
    """Test for school year editing view trying to make one school year overlap another.

    We get the school year container:

        >>> app = ISchoolToolApplication(None)
        >>> syc = ISchoolYearContainer(app)

    Add a a couple of school years

        >>> syc['2005-2006'] = SchoolYear("2005-2006",
        ...                               date(2005, 9, 1),
        ...                               date(2006, 7, 16))
        >>> sy = syc['2006-2007'] = SchoolYear("2006-2007",
        ...                               date(2006, 9, 1),
        ...                               date(2007, 7, 16))

    Fill in the form so that one of the school years would overlap the
    other one

        >>> request = TestRequest()
        >>> directlyProvides(request, [ISchoolToolSkin])
        >>> request.form = {'form.buttons.apply': u'Apply',
        ...                 'form.widgets.title': u'2006-2007',
        ...                 'form.widgets.first': u'2006-07-15',
        ...                 'form.widgets.last' : u'2007-07-15'}

    And submit it

        >>> view = SchoolYearEditView(sy, request)
        >>> view.update()

    An error message will get displayed

        >>> for error in view.widgets.errors: print error.render()
        <div class="error">
        Date range you have selected overlaps with the following school years:
        <div> <a href="http://127.0.0.1/schoolyears/2005-2006">2005-2006</a> (2005-09-01 &mdash; 2006-07-16) </div>
        </div>

    And the school year will not get modified

        >>> sy.title, sy.first, sy.last
        ('2006-2007', datetime.date(2006, 9, 1), datetime.date(2007, 7, 16))

    """


def test_suite():
    optionflags = doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS
    suite = doctest.DocTestSuite(optionflags=optionflags,
                                 extraglobs={'provideAdapter': provideStubAdapter,
                                             'provideUtility': provideStubUtility},
                                 setUp=setUp, tearDown=tearDown)
    suite.layer = schoolyear_functional_layer
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
