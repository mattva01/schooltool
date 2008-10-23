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

from schooltool.common import parse_date


class IDateTextWidget(Interface):
    pass


from z3c.form.browser.text import TextWidget
class CustomDateTextWidget(TextWidget):
    implements(IDateTextWidget)


def CustomDateFieldTextWidget(field, request):
    """IFieldWidget factory for MyWidget."""
    from z3c.form.widget import FieldWidget
    return FieldWidget(field, CustomDateTextWidget(request))


from z3c.form.converter import BaseDataConverter
from z3c.form.converter import FormatterValidationError
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
            raise FormatterValidationError(err.args[0], value)
