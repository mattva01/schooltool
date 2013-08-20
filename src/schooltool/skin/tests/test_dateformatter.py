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
Tests for DateFormatter views.
"""
import unittest
import doctest
import datetime

from zope.publisher.browser import TestRequest

from schooltool.app.browser.testing import setUp, tearDown
from schooltool.skin.dateformatter import DateFormatterFullView
from schooltool.skin.dateformatter import DateFormatterMediumView
from schooltool.skin.dateformatter import DateFormatterShortView
from schooltool.skin.dateformatter import LocaleLookupMixin


def doctest_DateFormatterView():
    r"""Test for DateFormatterView

    Let's say we need to localize the 1 december 2006

    We create 2 clients, one english, one french:

        >>> english_request = TestRequest(environ={'HTTP_ACCEPT_LANGUAGE':'en'})
        >>> french_request = TestRequest(environ={'HTTP_ACCEPT_LANGUAGE':'fr,en'})

    We setup the date:

        >>> date = datetime.date(2006, 12, 1)
        >>> date
        datetime.date(2006, 12, 1)
        >>> isinstance(date, datetime.date)
        True

    We take the Full format of a date:

        >>> view = DateFormatterFullView(date, english_request)
        >>> view()
        u'Friday, December 1, 2006'

    and in french:

        >>> view = DateFormatterFullView(date, french_request)
        >>> view()
        u'vendredi 1 d\xe9cembre 2006'

    We take the medium format of a date

        >>> view = DateFormatterMediumView(date, english_request)
        >>> view()
        u'Dec 1, 2006'

    and in french:

        >>> view = DateFormatterMediumView(date, french_request)
        >>> view()
        u'1 d\xe9c. 06'

    We take the short format of a date

        >>> view = DateFormatterShortView(date, english_request)
        >>> view()
        '2006-12-01'

    even in french the short format is ISO format:

        >>> view = DateFormatterShortView(date, french_request)
        >>> view()
        '2006-12-01'

    """

def doctest_LocaleLookupMixin():
    r"""Tests for LocaleLookupMixin

    Let's try first to use the mixin without a view and thus without
    a request attribute. This will fail as there is no request attribute
    provided

        >>> mixin = LocaleLookupMixin()
        >>> mixin.getLocale()
        Traceback (most recent call last):
            ...
        NotImplementedError: LocaleLookupMixin need to be applied on a view

    Now let's play with a real view which will use our LocaleLookupMixin

        >>> from zope.publisher.browser import BrowserView
        >>> class FooView(BrowserView, LocaleLookupMixin):
        ...     pass

    Let's create a dummy context for the view

        >>> class FooContext(object):
        ...     pass
        >>> barObj = FooContext()

    Let's create two simple request

        >>> french_request = TestRequest(environ={'HTTP_ACCEPT_LANGUAGE':'fr,en'})

    We can now instanciate the view

        >>> v = FooView(barObj, french_request)

        >>> locale = v.getLocale()

    We have then an instance of the Locale class

        >>> locale
        <zope.i18n.locales.Locale object ...>

    Which is french as in our request

        >>> locale.getLocaleID()
        u'fr'

    Now let's see what happen is no locale is defined in the request

        >>> simple_request = TestRequest()

    We don't have any language defined:

        >>> simple_request.locale.id.language is None
        True

    Let's see how the Mixin will behave, it should return an english
    locale by default:

        >>> v = FooView(barObj, simple_request)
        >>> locale = v.getLocale()
        >>> locale
        <zope.i18n.locales.Locale object ...>
        >>> locale.getLocaleID()
        'en_US'
    """

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocTestSuite(
        setUp=setUp, tearDown=tearDown,
        optionflags=doctest.ELLIPSIS|doctest.REPORT_NDIFF))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
