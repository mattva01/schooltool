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
"""Category Views

$Id$
"""
__docformat__ = 'reStructuredText'

import zope.interface
import zope.schema
from zope.app.form import utility

from schooltool import SchoolToolMessage as _
from schooltool.app import app
from schooltool.gradebook import category


def getKey(name):
    name = name.replace(' ', '')
    name = name.lower()
    return name.encode('utf-8')

class ICategoriesForm(zope.interface.Interface):
    """Schema for the form."""

    categories = zope.schema.Set(
        title=_('Categories'),
        value_type=zope.schema.Choice(
            vocabulary="schooltool.gradebook.categories")
        )

    newCategory = zope.schema.TextLine(
        title=_("New Category"))

    defaultCategory = zope.schema.Choice(
        title=_("Default Category"),
        vocabulary="schooltool.gradebook.categories")


class CategoryOverview(object):

    message = None

    def __init__(self, context, request):
        self.categories = category.getCategories(app.getSchoolToolApplication())
        super(CategoryOverview, self).__init__(context, request)

    def getData(self):
        return {'categories': [],
                'newCategory': '',
                'defaultCategory': self.categories.getDefaultKey()}

    def update(self):
        if 'REMOVE' in self.request:
            keys = utility.getWidgetsData(
                self, ICategoriesForm, names=['categories'])['categories']
            for key in keys:
                self.categories.delValue(key, 'en')
            self.message = _('Categories successfully deleted.')

        elif 'ADD' in self.request:
            value = utility.getWidgetsData(
                self, ICategoriesForm, names=['newCategory'])['newCategory']
            self.categories.addValue(getKey(value), 'en', value)
            self.message = _('Category successfully added.')

        elif 'CHANGE' in self.request:
            key = utility.getWidgetsData(self, ICategoriesForm,
                names=['defaultCategory'])['defaultCategory']
            self.categories.setDefaultKey(key)
            self.message = _('Default category successfully changed.')
