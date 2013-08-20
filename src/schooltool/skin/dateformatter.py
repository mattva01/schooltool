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
"""Language independent date formatting.
"""
from zope.publisher.browser import BrowserView

from zope.i18n.locales import Locale
from zope.i18n.locales import LocaleIdentity


class LocaleLookupMixin(object):
    """Mixin for extracting of locale from request.

    Defaults to english if no locale is set in the request.
    """

    def getLocale(self):
        if not hasattr(self, 'request'):
            raise NotImplementedError("LocaleLookupMixin need to be applied on a view")

        if self.request.locale.id.language is None:
            # if we dont have any locale defined in the request
            # we set default to english
            id = LocaleIdentity('en', territory='US')
            locale = Locale(id)
        else:
            if hasattr(self.request, 'locale'):
                locale = self.request.locale

        return locale


class DateFormatterFullView( BrowserView, LocaleLookupMixin):
    """Formats the date using the 'full' format"""

    def __call__(self):
        locale = self.getLocale()
        formatter = locale.dates.getFormatter('date','full')
        return formatter.format(self.context)


class DateFormatterLongView( BrowserView, LocaleLookupMixin):
    """Formats the date using the 'long' format"""

    def __call__(self):
        locale = self.getLocale()
        formatter = locale.dates.getFormatter('date','long')
        return formatter.format(self.context)


class DateFormatterMediumView( BrowserView, LocaleLookupMixin):
    """Formats the date using the 'medium' format"""

    def __call__(self):
        locale = self.getLocale()
        formatter = locale.dates.getFormatter('date','medium')
        return formatter.format(self.context)


class DateFormatterShortView( BrowserView, LocaleLookupMixin):
    """Formats the date using the 'short' format"""

    def __call__(self):
        return self.context.strftime("%Y-%m-%d")
