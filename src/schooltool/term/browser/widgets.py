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
Widgets.
"""
from zope.schema.interfaces import IDate
from zope.component import adapts
from zope.interface import implements
from zope.interface import Interface

from zc.datetimewidget.datetimewidget import DateWidget

from z3c.form.converter import BaseDataConverter
from z3c.form.converter import FormatterValidationError
from z3c.form.browser.text import TextWidget
from z3c.form.widget import FieldWidget

from schooltool.common import parse_date
from schooltool.common import SchoolToolMessage as _


class IDateTextWidget(Interface):
    pass


class CustomDateTextWidget(TextWidget, DateWidget):
    implements(IDateTextWidget)

    def date_selector_button(self):
        real_name = self.name
        self.name = self.id
        result = self._render("")
        self.name = real_name
        return result


def CustomDateFieldTextWidget(field, request):
    """IFieldWidget factory for MyWidget."""
    return FieldWidget(field, CustomDateTextWidget(request))


class CustomDateDataConverter(BaseDataConverter):
    """A special data converter for iso dates."""

    adapts(IDate, CustomDateTextWidget)

    def toWidgetValue(self, value):
        """See interfaces.IDataConverter"""
        if value is self.field.missing_value:
            return u''
        return value.strftime("%Y-%m-%d")

    def toFieldValue(self, value):
        """See interfaces.IDataConverter"""
        if value == u'':
            return self.field.missing_value
        try:
            return parse_date(value)
        except ValueError, err:
            raise FormatterValidationError(_("The datetime string did not match the pattern yyyy-mm-dd"),
                                           value)
